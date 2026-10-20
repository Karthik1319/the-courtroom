import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

NEBIUS_API_KEY = os.environ["NEBIUS_API_KEY"]
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]
NEBIUS_PROJECT_ID = os.environ["NEBIUS_PROJECT_ID"]

SANDBOX_BASE_URL = "https://api.tokenfactory.nebius.com/sandboxes/v1"

# Per Nebius Token Factory's documented per-model endpoints: Ultra and Super
# require the us-central1 regional URL; Nano uses the global URL.
NEBIUS_BASE_URL_GLOBAL = "https://api.tokenfactory.nebius.com/v1/"
NEBIUS_BASE_URL_REGIONAL = "https://api.tokenfactory.us-central1.nebius.com/v1/"

MODEL_JUDGE = "nvidia/Nemotron-3-Ultra-550b-a55b"
MODEL_PROSECUTOR = "nvidia/nemotron-3-super-120b-a12b"
MODEL_DEFENSE = "nvidia/nemotron-3-super-120b-a12b"
MODEL_FORMATTER = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"

# Defense panel: the models that each independently write a patch candidate
# per round (run in parallel; run_case keeps the best one that clears the
# gates). Super + Ultra give two different-strength reasoners. Nano is left
# out (too weak to patch reliably) and Lightning until its base URL is
# confirmed (see the open item in memory).
DEFENSE_PANEL_MODELS = [MODEL_DEFENSE, MODEL_JUDGE]  # Super, Ultra

# Supreme Court: three judges on DIFFERENT models each rate the severity of the
# confirmed vulnerabilities and write an opinion (they never re-decide guilt —
# that is computed deterministically). Different models give a real majority
# vs dissent. Lightning excluded until its base URL is confirmed.
JUDGE_PANEL_MODELS = [MODEL_JUDGE, MODEL_PROSECUTOR, MODEL_FORMATTER]  # Ultra, Super, Nano

# Ceiling on tokens a single agent call may emit. Nemotron reasoning models
# spend output tokens on visible reasoning, so this caps runaway cost. It is a
# safety ceiling, not a target — raise it if real runs show replies truncated
# before the final code block.
MAX_OUTPUT_TOKENS = 4096

# Which base URL each model needs.
MODEL_BASE_URL = {
    MODEL_JUDGE: NEBIUS_BASE_URL_REGIONAL,
    MODEL_PROSECUTOR: NEBIUS_BASE_URL_REGIONAL,
    MODEL_DEFENSE: NEBIUS_BASE_URL_REGIONAL,
    MODEL_FORMATTER: NEBIUS_BASE_URL_GLOBAL,
}


def get_client(model: str) -> OpenAI:
    """Return an OpenAI client pointed at the correct base URL for this model."""
    return OpenAI(base_url=MODEL_BASE_URL[model], api_key=NEBIUS_API_KEY)
