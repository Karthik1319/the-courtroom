import os

from dotenv import load_dotenv

load_dotenv()

NEBIUS_API_KEY = os.environ["NEBIUS_API_KEY"]
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"

MODEL_JUDGE = "nvidia/Nemotron-3-Ultra-550b-a55b"
MODEL_PROSECUTOR = "nvidia/nemotron-3-super-120b-a12b"
MODEL_DEFENSE = "nvidia/nemotron-3-super-120b-a12b"
MODEL_FORMATTER = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
