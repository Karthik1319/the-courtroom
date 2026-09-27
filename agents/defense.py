# Defense agent: patches the code the Prosecutor attacked,
# re-runs the exploit/test in the sandbox to prove the fix holds.

import re

import config
import tools.sandbox as sandbox_tool

client = config.get_client(config.MODEL_DEFENSE)

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
