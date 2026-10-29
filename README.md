# The Courtroom: Appeals

An adversarial, multi-round AI code auditor built for the **Nebius x NVIDIA Global AI Hackathon** (Coding and Agentic Engineering track).

You hand it a Python file. AI agents attack it, defend it, and appeal — over multiple rounds — and a **real Nebius Token Factory sandbox is the judge of what actually worked**. No agent grades its own homework.

> **The core idea:** most AI code-review tools describe a fix and ask you to trust it. The Courtroom *proves* every claim by executing it. An attack only counts if it extracts a secret planted by the harness; a patch is only accepted if a real sandbox run shows it blocks every known attack **and** keeps the app's normal behaviour working.

## How a case runs

```
            ┌─────────────────────────────────────────────────┐
            │  Round N (repeats until the code holds or breaks) │
            └─────────────────────────────────────────────────┘
  Prosecution ──> harness runs the attack in a sandbox ──> did it extract
   (Nemotron)      (planted secret flag, network off)       the flag?
       │                                                        │ yes
       │                                              exploit joins the suite
       ▼                                                        ▼
  Defense panel ──> harness grades each patch ──> accept only if it blocks
  (models in        (replays the WHOLE exploit      the whole suite AND
   parallel)         suite + behaviour test)        passes behaviour
       │                                                        │
       └────────────── appeal: attack the new code next round ─┘

  When no attack lands  ->  CASE CLOSED
  When no patch holds   ->  GUILTY BUT UNFIXED
                 │
                 ▼
  Verdict is computed deterministically from the sandbox facts (never voted).
                 │
                 ▼
  Real-world precedent pulled live from Tavily (CVEs / known patterns)
                 │
                 ▼
  Supreme Court: three judges on different models rate SEVERITY and write a
  majority opinion + a dissent (they never re-decide guilt).
```

## What makes it different

- **The sandbox is the oracle, not the model.** The harness plants a fresh random secret for every run and only counts an attack if that secret comes back through the app's own interface. A model cannot fake success.
- **It catches fixes that *look* right but aren't.** Every patch is replayed against the full exploit suite and a normal-behaviour test in a real sandbox. Patches that break a feature, fail to run, or leave any exploit open are rejected — the `naive✗` / `broke✗` columns in the eval make this visible.
- **The verdict is deterministic.** Guilt is computed from sandbox facts, so it can never tie or be argued. LLMs are only used where judgement genuinely helps — rating *severity* — and their disagreement is shown openly as a majority and a dissent.
- **Grounded in reality.** Before sentencing, the system makes a live [Tavily](https://tavily.com) search for documented CVEs and attack patterns for the confirmed vulnerability class, so severity is anchored to real-world precedent.

## Tech stack

- **Nebius Token Factory** — hosts the NVIDIA Nemotron models and the sandboxes that execute every attack and patch.
  - `nvidia/Nemotron-3-Ultra-550b-a55b` and `nvidia/nemotron-3-super-120b-a12b` — the **defense panel** (two different-strength reasoners write patches in parallel each round).
  - `nvidia/nemotron-3-super-120b-a12b` — the **prosecution** (writes the attacks) and the **precedent query**.
  - `nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` — the **Supreme Court** severity panel (three different models → a real majority and dissent).
  - **Token Factory Sandboxes** — run every attack/patch in an isolated container with outbound networking disabled, returning real `stdout` / `stderr` / `exit_code`.
- **Tavily API** — live web search for CVE / vulnerability precedent that grounds the severity ruling.

## Scope

Focused, by design: **Python targets**, and vulnerability classes where a naive fix often fails — demonstrated on a small notes app (`examples/vulnerable_notes.py`) carrying an **IDOR** (missing ownership check) and a **path traversal** bug.

## Setup

Requires Python 3 and a Nebius Token Factory account.

```bash
git clone https://github.com/Karthik1319/the-courtroom.git
cd the-courtroom

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` (see `.env.example`) with three values:

```bash
cat > .env << 'EOF'
NEBIUS_API_KEY=your_nebius_token_factory_api_key
TAVILY_API_KEY=your_tavily_api_key
NEBIUS_PROJECT_ID=your_nebius_project_id
EOF
```

- Get a **Nebius API key** and **project ID** from the [Nebius Token Factory](https://tokenfactory.nebius.com) console (the project ID appears on the console's Endpoints page).
- Get a **Tavily API key** at [tavily.com](https://tavily.com) (free tier available).

## Usage

Run a full trial and print the transcript:

```bash
python main.py examples/vulnerable_notes.py --behaviour examples/behaviour_notes.py
```

Add `--theatrical` for the animated, courtroom-styled view (used in the demo video); `--pace` controls the reveal speed:

```bash
python main.py examples/vulnerable_notes.py --behaviour examples/behaviour_notes.py --theatrical --pace 0.9
```

Compare defense configurations (Super-only vs Ultra-only vs the panel) on the same case:

```bash
python evaluate.py examples/vulnerable_notes.py --behaviour examples/behaviour_notes.py
```

## A note on reproducibility

The Nemotron-3 models are Mixture-of-Experts and are **non-deterministic even at temperature 0** on hosted inference (server-side expert routing varies with batching). Individual runs therefore differ — which is precisely why the system leans on an objective sandbox oracle rather than model self-assessment. The orchestrator retries the prosecution within a round so a flaky reply can't be mistaken for "no vulnerability."

## Project structure

```
main.py             # entry point: wires the model panels to the rounds loop + prints results
courtroom.py        # the rounds loop: attack -> verify -> patch -> appeal, deterministic verdict
evaluate.py         # compares defense configurations on one case
presenter.py        # the animated --theatrical view (rich)
config.py           # .env, model ids, per-model base URLs
agents/
  prosecutor.py     # writes the attacks (call()-based, sandbox-channel only)
  defense.py        # parallel defense panel — each model writes a patch candidate
  judge.py          # Supreme Court severity panel + live Tavily precedent research
tools/
  harness.py        # the oracle: plants a secret, runs attacks/patches, grades them
  sandbox.py        # runs code in a Nebius Token Factory sandbox (network off for attacks)
  search.py         # Tavily API wrapper
  scoring.py        # ranks gate-passing patches (Bandit findings, then diff size)
  parsing.py        # pulls code blocks out of model replies
examples/
  vulnerable_notes.py / behaviour_notes.py   # the multi-bug demo app + its behaviour test
  vulnerable_login.py / safe_login.py        # minimal single-bug and clean samples
```

## Demo

Demo video: _(YouTube link to be added)_

## License

MIT — see [LICENSE](LICENSE).
