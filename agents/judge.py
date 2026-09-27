# Judge agent: reviews the full trial transcript (search evidence,
# exploit, patch, re-test) and renders a verdict.

import config

client = config.get_client(config.MODEL_JUDGE)

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
