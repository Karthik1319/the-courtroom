# Entry point: runs the full Courtroom: Appeals loop on a target Python file.
#
#   prosecution panel -> run_attack (sandbox oracle) -> exploit suite grows
#   -> defense panel -> check_patch gates -> appeal -> ... -> deterministic verdict
#
# The loop itself lives in courtroom.run_case; this file only wires the model
# panels to it and prints the scoreboard.

import argparse
import difflib

import courtroom
from agents import defense, judge, prosecutor


def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


# --- panels: adapt the agents to the callables run_case expects -----------

def prosecute(current_code: str, brief: str) -> list[str]:
    """Attack panel. prosecutor.write_attack is the attack side (yours).

    It must return attack scripts (a list of strings, or one string) that use
    the harness `call(method, **kwargs)` channel to the target app.
    """
    if not hasattr(prosecutor, "write_attack"):
        raise SystemExit(
            "prosecutor.write_attack(current_code, brief) is not implemented yet.\n"
            "That's the attack side — it returns call()-based exploit scripts for the\n"
            "rounds loop. Implement it in agents/prosecutor.py, then re-run."
        )
    out = prosecutor.write_attack(current_code, brief)
    return out if isinstance(out, list) else [out]


def defend(current_code: str, exploits: list[str]) -> list[tuple[str, str]]:
    """Defense panel: each model in config.DEFENSE_PANEL_MODELS writes a patch
    candidate in parallel; run_case keeps the best one that clears the gates."""
    return defense.write_patch_panel(current_code, exploits)


# --- scoreboard -----------------------------------------------------------

def _summarize_case(result: courtroom.CaseResult) -> str:
    """Compact, facts-only summary for the judge panel — never raw transcripts."""
    lines = [
        f"Deterministic verdict: {result.verdict}",
        f"Confirmed exploits: {len(result.exploit_suite)}",
        "Attack vectors (one line each):",
    ]
    for i, script in enumerate(result.exploit_suite, 1):
        first = next((ln.strip() for ln in script.splitlines() if ln.strip()), "")
        lines.append(f"  {i}. {first[:80]}")
    lines.append("Rounds:")
    for r in result.rounds:
        lines.append(f"  R{r.number}: {r.attacks_worked} attack(s) worked, "
                     f"patch_accepted={r.patch_accepted}, winner={r.winning_model or '-'}")
    diff = list(difflib.unified_diff(
        result.original_code.splitlines(), result.final_code.splitlines(),
        fromfile="original", tofile="final", lineterm=""))
    capped = "\n".join(diff[:60]) if diff else "(no change)"
    lines.append("Original -> final diff (capped):\n" + capped)
    return "\n".join(lines)


def _print_supreme_court(panel) -> None:
    print()
    print("=" * 64)
    print(" SUPREME COURT — SEVERITY PANEL")
    print("=" * 64)
    if panel is None:
        print("(no opinions returned)")
        print("=" * 64)
        return
    print(f"Majority severity : {panel.majority_severity}")
    print(f"Majority opinion  : {panel.majority_opinion}")
    if panel.dissent:
        print(f"Dissent ({panel.dissent.model}, {panel.dissent.severity}): {panel.dissent.opinion}")
    else:
        print("Dissent           : none (unanimous)")
    print("-" * 64)
    print("Panel votes:")
    for o in panel.opinions:
        print(f"  {o.model:>28} : {o.severity}")
    print("=" * 64)


def _print_scoreboard(result: courtroom.CaseResult) -> None:
    print()
    print("=" * 64)
    print(" THE COURTROOM: APPEALS — SCOREBOARD")
    print("=" * 64)
    header = (f"{'round':>5} | {'attacks':>7} | {'worked':>6} | {'new':>3} | "
              f"{'patches':>7} | {'accepted':>8} | winner")
    print(header)
    print("-" * len(header))
    for r in result.rounds:
        print(f"{r.number:>5} | {r.attacks_tried:>7} | {r.attacks_worked:>6} | "
              f"{r.new_exploits:>3} | {r.patches_tried:>7} | "
              f"{('yes' if r.patch_accepted else 'no'):>8} | {r.winning_model}")
    print("-" * len(header))
    print(f"status         : {result.status}")
    print(f"exploits found : {len(result.exploit_suite)}")
    print(f"VERDICT        : {result.verdict}")
    print("=" * 64)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run The Courtroom: Appeals on a Python file.")
    parser.add_argument("target", help="path to the Python file on trial")
    parser.add_argument("--behaviour", help="path to a normal-behaviour test script (Round 0)")
    parser.add_argument("--rounds", type=int, default=3, help="max rounds (default 3)")
    args = parser.parse_args()

    source_code = _read(args.target)
    behaviour_tests = [_read(args.behaviour)] if args.behaviour else []

    print(f"The Courtroom is now in session for: {args.target}")
    if not behaviour_tests:
        print("(no behaviour test given — Round 0 baseline skipped; pass --behaviour to enable it)")

    result = courtroom.run_case(
        source_code=source_code,
        behaviour_tests=behaviour_tests,
        prosecute=prosecute,
        defend=defend,
        max_rounds=args.rounds,
    )
    _print_scoreboard(result)

    # Supreme Court only convenes when there is a confirmed vulnerability to rate.
    if result.exploit_suite:
        panel = judge.convene(_summarize_case(result))
        _print_supreme_court(panel)


if __name__ == "__main__":
    main()
