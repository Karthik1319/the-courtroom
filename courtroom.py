# The Courtroom: Appeals — rounds orchestration.
#
# Pure control flow. It owns the attack -> verify -> patch -> appeal loop, the
# stop rules, the growing exploit suite, and the deterministic verdict. It
# never decides success itself: tools.harness (the sandbox oracle) does. The
# model panels are INJECTED as callables, so this logic is fully testable
# without any API calls.

from dataclasses import dataclass, field

from tools import harness

# ---- case outcomes --------------------------------------------------------
CASE_CLOSED = "CASE_CLOSED"             # prosecution ran out of working attacks
GUILTY_UNFIXED = "GUILTY_BUT_UNFIXED"   # a working attack had no passing patch
MAX_ROUNDS = "MAX_ROUNDS"               # rounds exhausted with the code holding
BASELINE_INVALID = "BASELINE_INVALID"   # behaviour test failed on the original


@dataclass
class RoundRecord:
    number: int
    attacks_tried: int
    attacks_worked: int
    new_exploits: int
    patches_tried: int
    patch_accepted: bool
    winning_model: str = ""   # label of the panel model whose patch was adopted


@dataclass
class CaseResult:
    status: str
    verdict: str
    original_code: str
    final_code: str
    exploit_suite: list = field(default_factory=list)  # scripts that extracted the flag
    rounds: list = field(default_factory=list)          # list[RoundRecord]


def brief_lines(exploit_suite):
    """One short line per known exploit — the compact memory handed to a panel.

    The real memory is the exploit suite itself (harness replays every past
    attack mechanically); this is only a hint so a panel doesn't repeat work.
    """
    if not exploit_suite:
        return "- (none yet)"
    lines = []
    for i, script in enumerate(exploit_suite, 1):
        first = next((ln.strip() for ln in script.splitlines() if ln.strip()), "")
        lines.append(f"- known exploit #{i}: {first[:80]}")
    return "\n".join(lines)


def _best(accepted, current):
    """Among gate-passing (label, code) patches, prefer the smallest change.

    Placeholder ranking: later steps add cross-examination, payload fuzzing and
    Bandit before falling back to diff size.
    """
    return min(accepted, key=lambda lc: abs(len(lc[1]) - len(current)))


def _verdict(status, exploit_suite):
    """Decide the verdict deterministically from sandbox facts — no ties, no LLM."""
    found = len(exploit_suite) > 0
    if not found:
        return "NOT GUILTY — no vulnerability was ever demonstrated in the sandbox."
    if status == GUILTY_UNFIXED:
        return "GUILTY BUT UNFIXED — vulnerability confirmed; no patch blocked every exploit."
    n = len(exploit_suite)
    return f"GUILTY — {n} vulnerabilit{'y' if n == 1 else 'ies'} confirmed and fixed."


def run_case(source_code, behaviour_tests, prosecute, defend, max_rounds=3):
    """Run one case to a verdict.

    prosecute(current_code: str, brief: str) -> list[str]
        Returns candidate attack scripts (each uses the harness `call()` channel).
    defend(current_code: str, exploits: list[str]) -> list[tuple[str, str]]
        Returns candidate (model_label, patched_code) pairs from the panel.

    Returns a CaseResult.
    """
    base = harness.Target(name="baseline", source_code=source_code,
                          behaviour_tests=behaviour_tests)

    # Round 0: the behaviour test must be valid against the ORIGINAL code,
    # otherwise every later "passes_behaviour" gate is meaningless.
    if not harness.run_behaviour(base):
        return CaseResult(
            BASELINE_INVALID,
            "NO CASE — the behaviour test failed on the original code; fix the test first.",
            source_code, source_code,
        )

    current = source_code
    exploit_suite = []
    rounds = []
    status = MAX_ROUNDS

    for n in range(1, max_rounds + 1):
        t = harness.Target(name=f"round{n}", source_code=current,
                           behaviour_tests=behaviour_tests)

        attacks = prosecute(current, brief_lines(exploit_suite))
        worked = []
        new_exploits = 0
        for atk in attacks:
            if harness.run_attack(t, atk).extracted_flag:
                worked.append(atk)
                if atk not in exploit_suite:
                    exploit_suite.append(atk)
                    new_exploits += 1

        # Stop: prosecution found nothing that works against the current code.
        if not worked:
            rounds.append(RoundRecord(n, len(attacks), 0, 0, 0, False))
            status = CASE_CLOSED
            break

        # Defense panel: a patch is accepted only if it clears every gate
        # (blocks the WHOLE exploit suite, keeps behaviour, runs).
        patches = defend(current, worked)  # list[(label, code)]
        accepted = [
            (label, code) for (label, code) in patches
            if harness.check_patch(code, exploit_suite, behaviour_tests).accepted
        ]

        # Stop: a real vulnerability with no patch that holds.
        if not accepted:
            rounds.append(RoundRecord(n, len(attacks), len(worked),
                                      new_exploits, len(patches), False))
            status = GUILTY_UNFIXED
            break

        # Appeal: adopt the best surviving patch and let prosecution attack it
        # again next round.
        best_label, best_code = _best(accepted, current)
        current = best_code
        rounds.append(RoundRecord(n, len(attacks), len(worked),
                                  new_exploits, len(patches), True,
                                  winning_model=best_label))

    return CaseResult(status, _verdict(status, exploit_suite),
                      source_code, current, exploit_suite, rounds)
