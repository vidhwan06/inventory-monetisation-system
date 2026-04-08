import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global model instance (singleton pattern)
_model = None


def get_gemini_model():
    """
    Returns a shared Gemini model instance.
    Ensures:
    - API key is loaded only once
    - Model is reused across agents
    """

    global _model

    if _model is None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY not found in .env file")

        # Configure Gemini
        genai.configure(api_key=api_key)

        # Use stable & fast model
        _model = genai.GenerativeModel(
            model_name="gemini-1.5-flash"
        )

    return _model