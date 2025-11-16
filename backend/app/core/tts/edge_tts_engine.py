import edge_tts
import asyncio
from .base import TTSEngine

class EdgeTTSEngine(TTSEngine):
    """
    Concrete implementation of TTSEngine using the edge-tts library.
    """
    def __init__(self, voice: str, communicate_rate: str = "+0%", communicate_volume: str = "+0%"):
        self.voice = voice
        self.communicate_rate = communicate_rate
        self.communicate_volume = communicate_volume

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesizes text into MP3 audio bytes using edge-tts.
        """
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.communicate_rate,
            volume=self.communicate_volume
        )
        audio_bytes_list = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes_list.append(chunk["data"])
        return b"".join(audio_bytes_list)

if __name__ == "__main__":
    # Example usage (for testing purposes)
    async def main():
        engine = EdgeTTSEngine(voice="en-US-AriaNeural")
        print("Synthesizing 'Hello, world! This is a test.'")
        audio_data = await engine.synthesize("Hello, world! This is a test.")
        with open("test_edge_tts.mp3", "wb") as f:
            f.write(audio_data)
        print("Audio saved to test_edge_tts.mp3")

    asyncio.run(main())
