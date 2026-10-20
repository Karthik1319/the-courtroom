import base64
import secrets
from dataclasses import dataclass, field
from tools import sandbox

# Marker the launcher prints on the sandbox's stdout. It carries a base64 blob
# of everything the SERVER sent back. The oracle reads ONLY this — never the
# attack's own stdout — so a cheating attack that reads the DB/file directly
# cannot score: its output never passes through the server channel.
TRANSCRIPT_MARKER = "COURTROOM_TRANSCRIPT:"

# Runs as the SERVER subprocess inside the sandbox. It holds the planted secret
# (in the app's in-memory store / a private temp dir) and answers one JSON
# request per line on stdin, writing one JSON reply per line on stdout.
#
# App contract this expects (you add these two small hooks to the target app):
#   * NotesApp(base_dir=...)      -- file ops rooted at an injected dir
#   * app.seed_secret(flag)       -- stores the secret in the instance's store
# Raw string so the "\n" below stays as source text, not a real newline.
_SERVER_RUNNER = r'''import json, os, sys
import target_app

flag = os.environ["COURTROOM_FLAG"]
root = os.environ["COURTROOM_ROOT"]

app = target_app.NotesApp(base_dir=os.path.join(root, "var", "notes"))
app.seed_secret(flag)

for line in sys.stdin:
    try:
        req = json.loads(line)
        name = req["method"]
        # allowlist: no dunder/private internals, and no re-seeding
        if name.startswith("_") or name == "seed_secret":
            raise PermissionError("method not exposed")
        result = getattr(app, name)(**req.get("kwargs", {}))
    except Exception as exc:
        result = "ERROR: " + str(exc)
    sys.stdout.write(json.dumps({"result": result}) + "\n")
    sys.stdout.flush()
'''


@dataclass
class Target:
    name: str
    source_code: str
    behaviour_tests: list[str] = field(default_factory=list)

@dataclass
class AttackResult:
    extracted_flag: bool
    flag: str | None
    exit_code: int
    stdout: str
    stderr: str
    label: str = ""

@dataclass
class PatchGates:
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
    return f"FLAG_{secrets.token_hex(8)}"

def run_attack(target: Target, attack_script: str) -> AttackResult:
    """Run one attack against the target in a subprocess-isolated sandbox.

    The target app runs as a SERVER subprocess that owns the secret; the attack
    gets only a call() channel to it. An attack "counts" (extracted_flag=True)
    only if the flag comes back THROUGH that channel — i.e. the bug was really
    used. Reading the planted DB/file directly lands in the attack's own stdout,
    which the oracle ignores.
    """
    flag = plant_flag()
    source_b64 = base64.b64encode(target.source_code.encode("utf-8")).decode("ascii")
    attack_b64 = base64.b64encode(attack_script.encode("utf-8")).decode("ascii")
    server_b64 = base64.b64encode(_SERVER_RUNNER.encode("utf-8")).decode("ascii")

    # The launcher is itself a Python program we run in the sandbox. Literal
    # braces for JSON/dicts are doubled ({{ }}) because this is an f-string.
    launcher = f'''import base64, json, os, subprocess, sys, tempfile

FLAG = {flag!r}

with open("target_app.py", "w") as f:
    f.write(base64.b64decode("{source_b64}").decode("utf-8"))
with open("server_runner.py", "w") as f:
    f.write(base64.b64decode("{server_b64}").decode("utf-8"))

# Private home for the FILE-based bug: a random dir the attack is not told.
root = tempfile.mkdtemp(prefix="srv_")
os.makedirs(os.path.join(root, "var", "notes"), exist_ok=True)
os.makedirs(os.path.join(root, "etc"), exist_ok=True)
with open(os.path.join(root, "etc", "passwd"), "w") as f:
    f.write("root:x:0:0:root:/root:/bin/bash\\nadmin_flag:" + FLAG)

# Secret + root reach the SERVER via its child env only (not our os.environ),
# so the attack (which runs in THIS process) can't read them from its own env.
env = dict(os.environ, COURTROOM_FLAG=FLAG, COURTROOM_ROOT=root)
server = subprocess.Popen(
    [sys.executable, "server_runner.py"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env, text=True,
)

transcript = []  # the ONLY thing the oracle reads: the server's replies

def call(method, **kwargs):
    server.stdin.write(json.dumps({{"method": method, "kwargs": kwargs}}) + "\\n")
    server.stdin.flush()
    reply = server.stdout.readline()
    transcript.append(reply)
    return json.loads(reply)["result"]

attack_code = base64.b64decode("{attack_b64}").decode("utf-8")
try:
    exec(attack_code, {{"call": call, "__name__": "__attack__"}})
except Exception as exc:
    sys.stderr.write("attack error: " + str(exc))
finally:
    try:
        server.stdin.close()
        server.terminate()
    except Exception:
        pass

print("{TRANSCRIPT_MARKER}" + base64.b64encode("".join(transcript).encode("utf-8")).decode("ascii"))
'''

    try:
        result = sandbox.run_python(launcher, disable_network=True)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code", 1)
    except Exception as exc:
        stdout = ""
        stderr = str(exc)
        exit_code = 1

    # Oracle: did the flag come back through the SERVER channel (the transcript)?
    transcript_text = ""
    for line in stdout.splitlines():
        if line.startswith(TRANSCRIPT_MARKER):
            transcript_text = base64.b64decode(line[len(TRANSCRIPT_MARKER):]).decode("utf-8")

    extracted = flag in transcript_text

    return AttackResult(
        extracted_flag=extracted,
        flag=flag,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        label="Pending evaluation",
    )

def run_behaviour(target: Target) -> bool:
    if not target.behaviour_tests:
        return True

    source_b64 = base64.b64encode(target.source_code.encode('utf-8')).decode('ascii')

    for test_script in target.behaviour_tests:
        test_b64 = base64.b64encode(test_script.encode('utf-8')).decode('ascii')
        full_script = f"""import base64
with open('target_app.py', 'w') as f:
    f.write(base64.b64decode('{source_b64}').decode('utf-8'))

test_code = base64.b64decode('{test_b64}').decode('utf-8')
exec(test_code)
"""
        try:
            result = sandbox.run_python(full_script, disable_network=True)
            if result.get("exit_code", 1) != 0:
                return False
        except Exception:
            return False

    return True

def check_patch(
    patched_code: str,
    exploit_suite: list[str],
    behaviour_tests: list[str],
) -> PatchGates:
    target = Target(name="patched_app", source_code=patched_code, behaviour_tests=behaviour_tests)

    source_b64 = base64.b64encode(patched_code.encode('utf-8')).decode('ascii')
    syntax_script = f"""import base64
with open('target_app.py', 'w') as f:
    f.write(base64.b64decode('{source_b64}').decode('utf-8'))
import target_app
print('SYNTAX_OK')
"""

    try:
        syntax_check = sandbox.run_python(syntax_script, disable_network=True)
        runs_without_crash = syntax_check.get("exit_code", 1) == 0
    except Exception:
        runs_without_crash = False

    if not runs_without_crash:
        return PatchGates(blocks_all_exploits=False, passes_behaviour=False, runs_without_crash=False)

    passes_behaviour = run_behaviour(target)

    blocks_all_exploits = True
    for exploit in exploit_suite:
        attack_result = run_attack(target, exploit)
        if attack_result.extracted_flag:
            blocks_all_exploits = False
            break

    return PatchGates(
        blocks_all_exploits=blocks_all_exploits,
        passes_behaviour=passes_behaviour,
        runs_without_crash=runs_without_crash,
    )
