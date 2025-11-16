from abc import ABC, abstractmethod

class TTSEngine(ABC):
    """
    Abstract Base Class for Text-to-Speech engines.
    Defines the interface for TTS synthesis.
    """
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesizes text into audio bytes.

        Args:
            text: The text string to synthesize.

        Returns:
            Raw audio data as bytes (e.g., MP3 format).
        """
        pass
