# ai-agents\models\gemini_langchain.py

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from ai_agents.configs.models_config import GEMINI_API_KEY, GEMINI_TEMPERATURE, GEMINI_MODEL
import time

def get_langchain_gemini():
    """
    Initialize and return a ChatGoogleGenerativeAI instance.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables")
        
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=GEMINI_TEMPERATURE,
        google_api_key=GEMINI_API_KEY,
        timeout=30  # Add a 30-second timeout
    )
