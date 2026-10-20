# Patch-scoring: rank the patches that already cleared run_case's gates.
#
# These are the DEFENSIVE ranking signals from the plan:
#   * Bandit  — fewer static-analysis findings is better (a security linter;
#               it analyses the AST, it does NOT run the code).
#   * diff    — a smaller change from the current code is better.
#
# The other two planned signals are attack-side and intentionally NOT here:
# cross-examination (next round's prosecutors attack the survivors) happens
# naturally via the rounds loop's appeal, and payload fuzzing is the user's.
#
# Bandit runs on the orchestrator host (not the sandbox): it is static analysis,
# not model inference or code execution, and it degrades gracefully to a
# diff-only ranking when bandit is not installed.

import difflib
import json
import os
import shutil
import subprocess
import tempfile


def bandit_findings(code: str):
    """Number of Bandit findings in `code`, or None if bandit is unavailable."""
    if shutil.which("bandit") is None:
        return None
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            path = f.name
        # bandit exits non-zero when it finds issues; we read its JSON regardless.
        proc = subprocess.run(
            ["bandit", "-f", "json", "-q", path],
            capture_output=True, text=True,
        )
        data = json.loads(proc.stdout or "{}")
        return len(data.get("results", []))
    except Exception:
        return None
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


def diff_size(current: str, candidate: str) -> int:
    """Number of added/removed lines between current code and a candidate."""
    diff = difflib.unified_diff(
        current.splitlines(), candidate.splitlines(), lineterm=""
    )
    return sum(
        1 for line in diff
        if line[:1] in ("+", "-") and not line.startswith(("+++", "---"))
    )


def rank(candidates, current):
    """Order gate-passing (label, code) patches best-first.

    Sort by (Bandit findings, diff size). If Bandit is unavailable for any
    candidate, fall back to diff size alone so ranking still works.
    """
    scored = [
        (label, code, bandit_findings(code), diff_size(current, code))
        for label, code in candidates
    ]
    if scored and all(s[2] is not None for s in scored):
        scored.sort(key=lambda s: (s[2], s[3]))
    else:
        scored.sort(key=lambda s: s[3])
    return [(label, code) for label, code, _b, _d in scored]
