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
