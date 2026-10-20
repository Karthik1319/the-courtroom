# Step 6: the eval table.
#
# Runs the SAME case under several defense configurations and tabulates the
# outcomes, so the ensemble claim is backed by data rather than assertion:
#   Super-only vs Ultra-only vs the Super+Ultra panel.
#
# The prosecutor is held fixed across configs (only the DEFENSE side varies),
# so differences in the table are attributable to the defense configuration.
# Judges are not convened here — the table is about defense outcomes, and
# skipping them saves tokens.
#
# NOTE: running this spends API tokens (each config runs the full loop:
# prosecutor + defense calls + sandbox runs). Building/importing it does not.

import argparse

import config
import courtroom
import main  # reuse main.prosecute (the prosecutor adapter)
from agents import defense

EVAL_CONFIGS = [
    ("Super-only", [config.MODEL_DEFENSE]),
    ("Ultra-only", [config.MODEL_JUDGE]),
    ("Panel (Super+Ultra)", config.DEFENSE_PANEL_MODELS),
]

_RESULT_LABEL = {
    courtroom.CASE_CLOSED: "FIXED",
    courtroom.GUILTY_UNFIXED: "UNFIXED",
    courtroom.MAX_ROUNDS: "HELD (max rounds)",
    courtroom.BASELINE_INVALID: "NO CASE",
}


def _defend_with(models):
    """A defend() adapter bound to a specific set of defense models."""
    def defend(current_code, exploits):
        return defense.write_patch_panel(current_code, exploits, models=models)
    return defend


def _result_label(result):
    if result.status == courtroom.CASE_CLOSED and not result.exploit_suite:
        return "NO VULN FOUND"
    return _RESULT_LABEL.get(result.status, result.status)


def run_eval(source_code, behaviour_tests, configs=None, max_rounds=3):
    """Run the case once per config; return a list of (name, CaseResult)."""
    configs = configs or EVAL_CONFIGS
    rows = []
    for name, models in configs:
        result = courtroom.run_case(
            source_code, behaviour_tests,
            main.prosecute, _defend_with(models), max_rounds,
        )
        rows.append((name, result))
    return rows


def print_table(rows):
    print()
    print("=" * 78)
    print(" EVALUATION — DEFENSE CONFIGURATIONS ON THE SAME CASE")
    print("=" * 78)
    header = (f"{'config':<22}| {'result':<14}| {'expl':>4}| {'rnds':>4}| "
              f"{'accepted':>8}| {'naive✗':>6}| {'broke✗':>6}")
    print(header)
    print("-" * len(header))
    for name, r in rows:
        broke = r.patches_rejected_behaviour + r.patches_rejected_crash
        print(f"{name:<22}| {_result_label(r):<14}| {len(r.exploit_suite):>4}| "
              f"{len(r.rounds):>4}| {r.patches_accepted:>8}| "
              f"{r.patches_rejected_naive:>6}| {broke:>6}")
    print("-" * len(header))
    print("naive✗ = fixes that kept behaviour but did NOT block every exploit (caught by the harness)")
    print("broke✗ = fixes that broke a normal feature or failed to run (caught by the harness)")
    print("=" * 78)


def main_cli():
    parser = argparse.ArgumentParser(description="Compare defense configs on one case.")
    parser.add_argument("target", help="path to the Python file on trial")
    parser.add_argument("--behaviour", help="path to a normal-behaviour test script")
    parser.add_argument("--rounds", type=int, default=3, help="max rounds (default 3)")
    args = parser.parse_args()

    with open(args.target) as f:
        source_code = f.read()
    behaviour_tests = []
    if args.behaviour:
        with open(args.behaviour) as f:
            behaviour_tests = [f.read()]

    print(f"Evaluating defense configurations on: {args.target}")
    rows = run_eval(source_code, behaviour_tests, max_rounds=args.rounds)
    print_table(rows)


if __name__ == "__main__":
    main_cli()
