import base64
import secrets
from dataclasses import dataclass, field
from tools import sandbox

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
    flag = plant_flag()
    source_b64 = base64.b64encode(target.source_code.encode('utf-8')).decode('ascii')
    attack_b64 = base64.b64encode(attack_script.encode('utf-8')).decode('ascii')
    
    full_script = f"""import os
import sqlite3
import base64

# 1. Isolate target app into a module to prevent shared namespace cheating
with open('target_app.py', 'w') as f:
    f.write(base64.b64decode('{source_b64}').decode('utf-8'))

# 2. Plant IDOR flag in a persistent SQLite database
conn = sqlite3.connect('notes.db')
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, owner TEXT, content TEXT)")
c.execute("INSERT INTO notes (owner, content) VALUES ('admin', '{flag}')")
conn.commit()
conn.close()

# 3. Plant Path Traversal flag in filesystem
os.makedirs('/tmp/system_root/etc', exist_ok=True)
with open('/tmp/system_root/etc/passwd', 'w') as f:
    f.write('root:x:0:0:root:/root:/bin/bash\\nadmin_flag:{flag}')

# 4. Execute the attack script in isolation
attack_code = base64.b64decode('{attack_b64}').decode('utf-8')
exec(attack_code)
"""
    
    try:
        result = sandbox.run_python(full_script, disable_network=True)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code", 1)
    except Exception as e:
        stdout = ""
        stderr = str(e)
        exit_code = 1
        
    extracted = flag in stdout
    
    return AttackResult(
        extracted_flag=extracted,
        flag=flag,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        label="Pending evaluation" 
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
        runs_without_crash=runs_without_crash
    )