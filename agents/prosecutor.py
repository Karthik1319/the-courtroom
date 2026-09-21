# Prosecutor agent: finds injection/auth bugs in Python code,
# searches Tavily for real-world precedent, writes an exploit/test.

import config
import tools.search as search_tool

client = config.get_client(config.MODEL_PROSECUTOR)

QUERY_SYSTEM_PROMPT = """You are the Prosecutor in an adversarial code review "trial".
Look at the given Python source code and identify the single most serious
injection bug (SQL injection, command injection, etc.) or authentication/
authorization bug (broken auth checks, missing permission checks, etc.).
Ignore all other bug types.

If you find no such vulnerability, respond with exactly: NONE

Otherwise, respond with ONLY a short web search query (5-12 words) to find
real-world precedent (e.g. known CVEs, common attack patterns) for this
exact type of vulnerability. Do not include any other text or explanation.
"""

ANALYSIS_SYSTEM_PROMPT = """You are the Prosecutor in an adversarial code review "trial".
You are given a Python source file and real-world search results about a
related vulnerability class. Your job is to find injection bugs (SQL
injection, command injection, etc.) or authentication/authorization bugs
(broken auth checks, missing permission checks, etc.) — ignore all other
bug types.

If you find a real vulnerability:
1. Name the specific vulnerability and where it is (function/line).
2. Explain in 1-2 sentences why it's exploitable, citing the search results
   if they're relevant (e.g. "this matches CVE-XXXX-XXXXX" or a known
   attack pattern).
3. Write a short Python script that demonstrates the exploit against the
   vulnerable function (assume it can be imported directly).

If you find no such vulnerability, say so clearly and explain why the code
is safe from injection/auth bugs.
"""


def _get_search_query(source_code: str) -> str:
    response = client.chat.completions.create(
        model=config.MODEL_PROSECUTOR,
        messages=[
            {"role": "system", "content": QUERY_SYSTEM_PROMPT},
            {"role": "user", "content": f"```python\n{source_code}\n```"},
        ],
    )
    return response.choices[0].message.content.strip()


def _format_evidence(search_result: dict) -> str:
    answer = search_result.get("answer")
    results = search_result.get("results") or []
    if not answer and not results:
        return "No search results found."

    lines = []
    if answer:
        lines.append(f"Summary: {answer}")
    if results:
        lines.append("Sources:")
        for r in results:
            lines.append(f"- {r.get('title', '')}: {r.get('url', '')}")
    return "\n".join(lines)


def analyze(source_code: str) -> str:
    query = _get_search_query(source_code)

    if query.upper() == "NONE":
        evidence_block = "No injection/auth vulnerability found; search skipped."
    else:
        search_result = search_tool.search(query)
        evidence_block = _format_evidence(search_result)

    user_content = (
        f"Here is the code to review:\n\n```python\n{source_code}\n```\n\n"
        f"Search query used: {query}\n\n"
        f"Real-world precedent found via web search:\n{evidence_block}"
    )

    response = client.chat.completions.create(
        model=config.MODEL_PROSECUTOR,
        messages=[
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content
