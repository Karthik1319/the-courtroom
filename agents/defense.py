# Defense agent: patches the code the Prosecutor attacked,
# re-runs the exploit/test in the sandbox to prove the fix holds.

import re
from concurrent.futures import ThreadPoolExecutor

import config
import tools.sandbox as sandbox_tool
from tools.parsing import extract_code_block

client = config.get_client(config.MODEL_DEFENSE)

# One client per model (each model may need a different base URL), built lazily.
_clients = {config.MODEL_DEFENSE: client}


def _client_for(model: str):
    if model not in _clients:
        _clients[model] = config.get_client(model)
    return _clients[model]

SYSTEM_PROMPT = """You are the Defense in an adversarial code review "trial".
You are given the original Python source code and the Prosecutor's findings,
which include a demonstrated exploit. Your job:

1. Write a corrected version of the source code that fixes the vulnerability
   the Prosecutor found (e.g. use parameterized queries instead of string
   formatting, add the missing auth check, etc.). Keep the same function
   names/signatures so it's a drop-in replacement.

2. Write ONE self-contained Python script that:
   - Includes the patched code inline (redefine the function(s) directly in
     the script — do not import from another file).
   - Retries the exact same attack the Prosecutor demonstrated against the
     patched code.
   - Prints exactly one final line: "RESULT: BLOCKED" if the attack no
     longer succeeds (e.g. it's rejected, raises a handled error, or returns
     no unauthorized data), or "RESULT: BYPASSED" if the attack still works.
   - Catches exceptions itself so the script always finishes and prints one
     of those two lines (don't let the script crash uncaught).

Respond in EXACTLY this format, with no extra commentary outside it:

### PATCHED_CODE
```python
<patched source code here>
```

### TEST_SCRIPT
```python
<self-contained test script here>
```

### EXPLANATION
<1-3 sentences on what you changed and why it fixes the vulnerability>
"""


def _extract_section(text: str, header: str) -> str:
    pattern = rf"### {header}\s*\n```(?:python)?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_explanation(text: str) -> str:
    match = re.search(r"### EXPLANATION\s*\n(.*)", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def patch(source_code: str, prosecutor_analysis: str) -> dict:
    user_content = (
        f"Original source code:\n\n```python\n{source_code}\n```\n\n"
        f"Prosecutor's findings:\n\n{prosecutor_analysis}"
    )

    response = client.chat.completions.create(
        model=config.MODEL_DEFENSE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    raw = response.choices[0].message.content

    patched_code = _extract_section(raw, "PATCHED_CODE")
    test_script = _extract_section(raw, "TEST_SCRIPT")
    explanation = _extract_explanation(raw)

    sandbox_result = sandbox_tool.run_python(test_script) if test_script else None

    return {
        "patched_code": patched_code,
        "test_script": test_script,
        "explanation": explanation,
        "sandbox_result": sandbox_result,
        "raw_response": raw,
    }


# --- v2: lean patch for the rounds loop -----------------------------------
# The harness grades the patch now (replays the whole exploit suite in the
# sandbox), so the Defense no longer writes or runs its own test. It just
# returns a drop-in patched source; courtroom.run_case decides if it holds.

PATCH_ONLY_PROMPT = """You are the Defense in an adversarial code review "trial".
You are given the current Python source code and a list of attack scripts that
currently extract a planted secret from it. Produce a corrected, drop-in
replacement for the WHOLE source file that fixes the underlying
vulnerabilities so those attacks no longer work, while keeping every function
and class name and signature identical and all normal behaviour intact.

Respond with ONLY one fenced Python code block containing the full patched
source, and no text outside it.
"""


def write_patch(current_code: str, exploits: list[str], model: str = config.MODEL_DEFENSE) -> str:
    """Return a single patched-source candidate from `model`.

    No self-grading: the harness verifies it. `exploits` are the attack scripts
    that currently succeed, given only as context for what to fix.
    """
    exploit_block = "\n\n".join(f"# attack {i + 1}\n{e}" for i, e in enumerate(exploits))
    user_content = (
        f"Current source code:\n\n```python\n{current_code}\n```\n\n"
        f"Attacks that currently succeed against it:\n\n```python\n{exploit_block}\n```"
    )
    response = _client_for(model).chat.completions.create(
        model=model,
        max_tokens=config.MAX_OUTPUT_TOKENS,
        messages=[
            {"role": "system", "content": PATCH_ONLY_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return extract_code_block(response.choices[0].message.content)


def _short(model: str) -> str:
    """Short, scoreboard-friendly label for a model id."""
    return model.split("/")[-1]


def write_patch_panel(current_code: str, exploits: list[str], models=None) -> list[tuple[str, str]]:
    """Run several models in parallel, each writing one patch candidate.

    Returns a list of (model_label, patched_code), de-duplicated by code so two
    models that produce identical patches collapse to one entry. A model that
    errors or returns nothing is skipped. courtroom.run_case decides which of
    these candidates (if any) actually clears the gates.
    """
    models = models or config.DEFENSE_PANEL_MODELS

    def _one(model):
        try:
            return _short(model), write_patch(current_code, exploits, model=model)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=len(models)) as pool:
        results = list(pool.map(_one, models))

    candidates = []
    seen_code = set()
    for item in results:
        if item is None:
            continue
        label, code = item
        if not code or code in seen_code:
            continue
        seen_code.add(code)
        candidates.append((label, code))
    return candidates
