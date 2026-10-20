# Harness interface for The Courtroom: Appeals (v2).
#
# This file is a CONTRACT only: it defines the data shapes and function
# signatures the rounds loop in main.py depends on. The bodies are left
# unimplemented on purpose — you fill them in. Nothing in here attacks code
# or plants bugs; it only describes how the orchestrator asks the harness
# "did this script leak the planted secret?" and "does this patch hold up?".
#
# Design rule this enforces: no agent grades its own work. Agents return a
# script (a string); the harness runs it in the sandbox and decides pass/fail
# by checking for the secret flag. See tools/sandbox.py:run_python for the
# runner the implementation should call.

from dataclasses import dataclass, field


@dataclass
class Target:
    """The code currently on trial for one case.

    `source_code` is the whole app being attacked and patched. It changes
    every round as the Defense patches it; the loop passes the latest version
    back in. `behaviour_tests` are scripts that must keep passing (normal
    features still work) — a patch that breaks one is rejected.
    """

    name: str
    source_code: str
    behaviour_tests: list[str] = field(default_factory=list)


@dataclass
class AttackResult:
    """Outcome of running one Prosecution script against a Target.

    `extracted_flag` is the only thing that makes an attack "count": it is
    True only when the script got the planted secret out. `label` is the
    one-line summary that joins the compact brief and the exploit suite
    (e.g. "R1 path traversal via '....//' -> leaked flag").
    """

    extracted_flag: bool
    flag: str | None
    exit_code: int
    stdout: str
    stderr: str
    label: str = ""


@dataclass
class PatchGates:
    """Pass/fail gates for one Defense patch. All three must be True to accept.

    These are hard gates, not rankings. Ranking the survivors (cross-exam,
    fuzzing, Bandit, smallest diff) happens in the scoring pipeline, not here.
    """

    blocks_all_exploits: bool
    passes_behaviour: bool
    runs_without_crash: bool

    @property
    def accepted(self) -> bool:
        return (
            self.blocks_all_exploits
            and self.passes_behaviour
            and self.runs_without_crash
        )


def plant_flag() -> str:
    """Return a fresh, unguessable secret for one sandbox run.

    Implementation note: generate it randomly per run (e.g. secrets.token_hex)
    so an agent can't hard-code or fake the flag. The same string is seeded
    into the sandbox (a DB row, a secret file, or a 'pwned' marker, depending
    on the bug class) and then looked for in an AttackResult.
    """
    raise NotImplementedError


def run_attack(target: Target, attack_script: str) -> AttackResult:
    """Run one Prosecution script against `target` in an isolated sandbox.

    Must: plant a fresh flag, make `target.source_code` importable, run
    `attack_script` via tools.sandbox.run_python with networking disabled,
    then set extracted_flag=True only if the planted flag appears in stdout.
    Returns an AttackResult. Does NOT raise on a failed exploit — a clean
    miss is a normal result (extracted_flag=False).
    """
    raise NotImplementedError


def run_behaviour(target: Target) -> bool:
    """Run every script in `target.behaviour_tests` against `target.source_code`.

    Returns True only if all of them exit cleanly (normal features work).
    Used both for the Round 0 baseline and as a patch gate.
    """
    raise NotImplementedError


def check_patch(
    patched_code: str,
    exploit_suite: list[str],
    behaviour_tests: list[str],
) -> PatchGates:
    """Decide whether a Defense patch is acceptable.

    Re-runs the whole growing `exploit_suite` against `patched_code` (this is
    the regression memory — none may still leak the flag), re-runs every
    behaviour test, and confirms the code imports/runs without crashing.
    Returns PatchGates; the caller reads `.accepted`.
    """
    raise NotImplementedError
