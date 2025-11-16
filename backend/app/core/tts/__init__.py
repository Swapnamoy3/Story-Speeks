import os
from .base import TTSEngine
from .edge_tts_engine import EdgeTTSEngine
from .gemini_tts_engine import GeminiTTSEngine

def get_tts_engine(voice: str = "en-US-AriaNeural") -> TTSEngine:
    """
    Factory function to get the configured TTS engine.
    Reads TTS_ENGINE environment variable.
    """
    tts_engine_name = os.getenv("TTS_ENGINE", "edge").lower()

    if tts_engine_name == "edge":
        return EdgeTTSEngine(voice=voice)
    elif tts_engine_name == "gemini":
        # You might need to pass API key or other configs here
        return GeminiTTSEngine()
    else:
        raise ValueError(f"Unsupported TTS_ENGINE: {tts_engine_name}")
