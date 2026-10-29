# Small shared helpers for pulling structured content out of model replies.

import re


def extract_code_block(text: str) -> str:
    """Return the first fenced code block in `text`, or the stripped text.

    Matches ```python ...``` or a bare ``` ...``` fence. Falls back to the
    whole stripped response when no fence is present, so callers always get a
    string (the sandbox will simply fail to run non-code, which is handled).

    Returns "" when `text` is None or empty. A Nemotron reasoning model
    occasionally returns null content (it spent its whole output budget on
    reasoning), and callers should get a harmless empty string, not a crash.
    """
    if not text:
        return ""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()
