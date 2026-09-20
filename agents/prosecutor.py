# Prosecutor agent: finds injection/auth bugs in Python code,
# searches Tavily for real-world precedent, writes an exploit/test.

import config

client = config.get_client(config.MODEL_PROSECUTOR)

SYSTEM_PROMPT = """You are the Prosecutor in an adversarial code review "trial".
You are given a Python source file. Your job is to find injection bugs
(SQL injection, command injection, etc.) or authentication/authorization bugs
(broken auth checks, missing permission checks, etc.) — ignore all other bug types.

If you find a real vulnerability:
1. Name the specific vulnerability and where it is (function/line).
2. Explain in 1-2 sentences why it's exploitable.
3. Write a short Python script that demonstrates the exploit against the
   vulnerable function (assume it can be imported directly).

If you find no such vulnerability, say so clearly and explain why the code
is safe from injection/auth bugs.
"""


def analyze(source_code: str) -> str:
    response = client.chat.completions.create(
        model=config.MODEL_PROSECUTOR,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Here is the code to review:\n\n```python\n{source_code}\n```"},
        ],
    )
    return response.choices[0].message.content
