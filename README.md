# The Courtroom

An adversarial multi-agent code auditor, built for the **Nebius x NVIDIA Global AI Hackathon** (Coding and Agentic Engineering track).

You give it a Python file. Three AI agents put it on trial:

1. **Prosecutor** finds an injection or authentication/authorization bug, searches the web (via [Tavily](https://tavily.com)) for real-world precedent (known CVEs, common attack patterns), and writes a working exploit.
2. **Defense** patches the code and writes a test that retries the exact same attack against the patch — which is then **actually executed in a real Nebius Token Factory sandbox**, not just trusted as a claim.
3. **Judge** reviews the full transcript — the search evidence, the exploit, the patch, and the real sandbox result — and renders a verdict.

The output is a full "trial transcript": a real vulnerability, grounded in real search evidence, fixed by a patch that's proven (via real code execution) to actually work.

## Why this exists

Most AI code review tools just describe a fix and ask you to trust it. The Courtroom instead **proves** the fix by running the original attack against the patched code in a live sandbox and showing you the real result.

## Tech stack

- **Nebius Token Factory** — hosts the NVIDIA Nemotron models (chat completions) and the sandbox used to execute code.
  - `nvidia/Nemotron-3-Ultra-550b-a55b` — the **Judge** (needs the strongest reasoning to weigh evidence).
  - `nvidia/nemotron-3-super-120b-a12b` — the **Prosecutor** and **Defense** (code generation + reasoning).
  - Nebius Token Factory **Sandboxes** — runs the generated exploit/patch-verification scripts in an isolated container and returns real `stdout`/`stderr`/`exit_code`.
- **Tavily API** — real web search for CVE/vulnerability precedent, used by the Prosecutor to ground its findings instead of reasoning in a vacuum.

## v1 scope

To keep this tractable, v1 intentionally only handles:
- **Python code**
- **Injection and authentication/authorization bugs** (e.g. SQL/command injection, broken auth checks)

## Setup

Requires Python 3 and a Nebius Token Factory account.

```bash
git clone <this-repo-url>
cd the-courtroom

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`) with three values:

```bash
cat > .env << 'EOF'
NEBIUS_API_KEY=your_nebius_token_factory_api_key
TAVILY_API_KEY=your_tavily_api_key
NEBIUS_PROJECT_ID=your_nebius_project_id
EOF
```

- Get a **Nebius API key** and **project ID** from the [Nebius Token Factory](https://tokenfactory.nebius.com) console (your project ID appears on the console's Endpoints page).
- Get a **Tavily API key** from [tavily.com](https://tavily.com) (free tier available).

## Usage

```bash
python main.py examples/vulnerable_login.py
```

This runs the full trial and prints the transcript to your terminal. Try it against `examples/safe_login.py` too — a clean file with no vulnerability, to see how the Courtroom handles a "not guilty" verdict.

## Project structure

```
main.py              # entry point: runs the full trial loop
config.py            # loads .env, model IDs, and the correct base URL per model
agents/
  prosecutor.py       # finds the bug, searches Tavily, writes the exploit
  defense.py          # patches the code, writes + runs a sandbox verification test
  judge.py            # renders the final verdict
tools/
  sandbox.py          # runs Python code in a real Nebius Token Factory sandbox
  search.py           # wraps the Tavily search API
examples/
  vulnerable_login.py # sample file with a real SQL injection bug
  safe_login.py       # sample file with no vulnerability
```

## License

MIT — see [LICENSE](LICENSE).
