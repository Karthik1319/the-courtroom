# Judge agent: reviews the full trial transcript (search evidence,
# exploit, patch, re-test) and renders a verdict.

import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import config

client = config.get_client(config.MODEL_JUDGE)

# One client per model (each may need a different base URL), built lazily.
_clients = {config.MODEL_JUDGE: client}


def _client_for(model: str):
    if model not in _clients:
        _clients[model] = config.get_client(model)
    return _clients[model]

SYSTEM_PROMPT = """You are the Judge in an adversarial code review "trial".
You are given the Prosecutor's findings (including a demonstrated exploit)
and the Defense's patch, along with the ACTUAL result of running the
Defense's test script in a real sandbox (not just their claim about it).

Render a verdict with this structure:

**Verdict:** [GUILTY (vulnerability confirmed and fixed) / GUILTY BUT UNFIXED
(vulnerability confirmed, but the sandbox result shows the patch did NOT
block the attack) / NOT GUILTY (no real vulnerability found)]

**Reasoning:** 2-4 sentences explaining your ruling. Base whether the fix
worked strictly on the actual sandbox RESULT line (BLOCKED or BYPASSED),
not on the Defense's explanation alone — if they disagree, trust the
sandbox result and call this out explicitly.

**Summary for the record:** 1 sentence, suitable as a headline for this case.
"""


def render_verdict(source_code: str, prosecutor_analysis: str, defense_result: dict) -> str:
    sandbox_result = defense_result.get("sandbox_result") or {}

    user_content = (
        f"Original code:\n\n```python\n{source_code}\n```\n\n"
        f"--- Prosecutor's findings ---\n{prosecutor_analysis}\n\n"
        f"--- Defense's patched code ---\n```python\n{defense_result.get('patched_code', '')}\n```\n\n"
        f"--- Defense's explanation ---\n{defense_result.get('explanation', '')}\n\n"
        f"--- Actual sandbox result of re-running the attack against the patch ---\n"
        f"exit_code: {sandbox_result.get('exit_code')}\n"
        f"stdout: {sandbox_result.get('stdout')}\n"
        f"stderr: {sandbox_result.get('stderr')}\n"
    )

    response = client.chat.completions.create(
        model=config.MODEL_JUDGE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content


# --- v2: Supreme Court severity panel --------------------------------------
# The guilt verdict is computed deterministically in courtroom.run_case. The
# judges here never touch guilt; they rate how SEVERE the confirmed findings
# are and write short opinions, from a compact facts summary (never raw
# transcripts). Three different models give a real majority vs dissent.

SEVERITY_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"]

JUDGE_PANEL_PROMPT = """You are a judge on the Supreme Court panel of an
adversarial code-review "trial". The guilt verdict has ALREADY been decided
from real sandbox facts — do NOT re-decide guilt. Your job is to rate the
SEVERITY of the confirmed vulnerabilities and give a brief opinion, using only
the case facts provided.

Respond in EXACTLY this format and nothing else:
SEVERITY: <one of CRITICAL, HIGH, MEDIUM, LOW, NONE>
OPINION: <2-3 sentences on real-world impact and the quality of the fix>
"""


@dataclass
class JudgeOpinion:
    model: str
    severity: str
    opinion: str


@dataclass
class JudgePanel:
    majority_severity: str
    majority_opinion: str
    dissent: "JudgeOpinion | None"
    opinions: list


def _parse_opinion(text: str):
    sev_match = re.search(r"SEVERITY:\s*(CRITICAL|HIGH|MEDIUM|LOW|NONE)", text, re.IGNORECASE)
    op_match = re.search(r"OPINION:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    severity = sev_match.group(1).upper() if sev_match else "UNKNOWN"
    opinion = op_match.group(1).strip() if op_match else text.strip()
    return severity, opinion


def _rate(model: str, case_summary: str):
    try:
        response = _client_for(model).chat.completions.create(
            model=model,
            max_tokens=config.MAX_OUTPUT_TOKENS,
            messages=[
                {"role": "system", "content": JUDGE_PANEL_PROMPT},
                {"role": "user", "content": case_summary},
            ],
        )
        severity, opinion = _parse_opinion(response.choices[0].message.content)
        return JudgeOpinion(model.split("/")[-1], severity, opinion)
    except Exception:
        return None


def _severity_rank(sev: str) -> int:
    return SEVERITY_LEVELS.index(sev) if sev in SEVERITY_LEVELS else len(SEVERITY_LEVELS)


def convene(case_summary: str, models=None) -> "JudgePanel | None":
    """Run the judge panel in parallel and assemble majority + dissent.

    Returns None if every judge failed. Majority severity is the most common
    vote, breaking ties toward the more severe level; the majority opinion is
    the strongest-model opinion in that group; the dissent is the first judge
    who voted a different severity (None if unanimous).
    """
    models = models or config.JUDGE_PANEL_MODELS

    with ThreadPoolExecutor(max_workers=len(models)) as pool:
        results = [o for o in pool.map(lambda m: _rate(m, case_summary), models) if o]

    if not results:
        return None

    counts = Counter(o.severity for o in results)
    # most votes wins; tie -> more severe (lower rank index)
    majority_severity = sorted(counts, key=lambda s: (-counts[s], _severity_rank(s)))[0]

    # majority opinion: keep panel model order (Ultra first) among the majority
    majority_group = [o for o in results if o.severity == majority_severity]
    majority_opinion = majority_group[0].opinion

    dissent = next((o for o in results if o.severity != majority_severity), None)

    return JudgePanel(majority_severity, majority_opinion, dissent, results)
