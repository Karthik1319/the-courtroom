# Feedback on Nebius & NVIDIA tooling

Honest, hands-on feedback from building **The Courtroom: Appeals** on Nebius Token Factory with NVIDIA Nemotron models. Written from real friction and real wins during development, not a checklist.

## Nebius Token Factory — model inference

**What worked well**
- **OpenAI-compatible API.** We used the stock `openai` Python client pointed at the Token Factory base URL — zero custom SDK, instant productivity.
- **Model range for cost routing.** Having Nemotron-3 in Ultra / Super / Nano sizes let us route by job: Super for the fast adversarial loop, Ultra where the strongest reasoning mattered, Nano for cheap formatting. This tiering is genuinely useful.
- **Reasoning quality.** On security tasks (spotting IDOR and path-traversal, writing defense-in-depth patches), Super and Ultra produced correct, well-reasoned fixes.

**Friction / suggestions**
- **Per-model base URLs are an undocumented gotcha.** Ultra and Super required the `us-central1` regional endpoint while Nano used the global one. We only found the right mapping from the per-model code samples in the dashboard; the main docs imply a single base URL. A clear per-model endpoint table in the docs would save hours.
- **MoE non-determinism even at `temperature=0`.** The Nemotron-3 models are Mixture-of-Experts, and hosted inference is not reproducible even at temperature 0 (expert routing appears to vary with server-side batching). This is reasonable given the architecture, but it should be **documented prominently**, because it directly affects anyone building evals or reproducible benchmarks.
- **Reasoning models can return `null` content.** When `max_tokens` is set too low, a reasoning model spends its whole budget thinking and returns empty `content`, which crashes naive parsing. Documenting a recommended minimum `max_tokens` for the reasoning models — and/or exposing `reasoning_content` separately and consistently — would help.

## Nebius Token Factory — Sandboxes

This was the most impressive piece of the stack for our use case (executing untrusted, AI-generated code).

**What worked well**
- **Real isolation, verified.** We tested it: parallel runs don't share a filesystem, and a run that deleted its own Python stdlib did not affect a later run from the same base image. Exactly what you want for running adversarial code.
- **Network kill-switch.** `networking: {enabled: false}` on spawn genuinely blocks egress (DNS fails) — essential for running attack code safely.
- **Branching from a result image works** and is powerful for "set up once, fork many times" workflows.
- **Cheap and fast** for short runs.

**Friction / suggestions**
- **The `Project` header requirement isn't obvious.** The sandbox API returns `400 Missing "Project" header` until you add it, and where to find the project ID isn't clearly documented (it's on the dashboard Endpoints page). Call this out in the quickstart.
- **`stdin` encoding must be `ascii` or `base64`** — passing `utf-8` returns a validation error. Minor, but a one-line note in the API reference would save a round of debugging.
- **The async spawn → poll → operation-result flow** (with the result arriving under `metadata.result`) took some reverse-engineering from the reference; a single end-to-end "run code and read stdout" example would be the highest-value addition to the docs.

## NVIDIA Nemotron models

- The Ultra / Super / Nano family is a great fit for multi-agent systems: you can give the hardest reasoning role to Ultra, run many Super calls in the adversarial loop, and use Nano for cheap support tasks.
- Using **three different models as independent judges** produced genuinely useful disagreement (a majority rating with a reasoned dissent), rather than three identical opinions — a real benefit of the model variety.

## Tavily

- `include_answer=True` was the right call: it returns a clean, pre-summarized answer so we didn't have to guess where to truncate raw result snippets.
- Integration was a single dependency and a few lines. It grounded our severity ratings in real CVEs (e.g. documented IDOR advisories) with almost no effort.
