# ai-agents\configs\models_config.py

import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "models/gemini-1.5-flash"
GEMINI_TEMPERATURE = 0.7