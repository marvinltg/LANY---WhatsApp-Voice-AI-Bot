import asyncio
import sounddevice as sd
import numpy as np
import logging
from src.audio.devices import find_device_index, get_audio_config

logger = logging.getLogger("LANY.AudioPlayback")

class AudioPlayer:
    def __init__(self, device_name: str | None = None):
        self.config = get_audio_config()
        self.device_idx = find_device_index(device_name, is_input=False) if device_name else None
        self.is_playing = False
        self._stop_event = asyncio.Event()

    async def play_pcm_data(self, pcm_bytes: bytes, sample_rate: int = 48000):
        if not pcm_bytes:
            return

        self.is_playing = True
        self._stop_event.clear()
        logger.info(f"Playing {len(pcm_bytes)} bytes of audio into virtual mic (device idx: {self.device_idx})...")

        # Convert 16-bit PCM bytes to numpy array
        audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)

        try:
            # Play using sounddevice built-in non-blocking play
            sd.play(audio_array, samplerate=sample_rate, device=self.device_idx)
            
            # Wait for playback to finish or be interrupted
            duration = len(audio_array) / sample_rate
            slept = 0.0
            
            while slept < duration and self.is_playing:
                if self._stop_event.is_set():
                    logger.info("Playback interrupted!")
                    sd.stop()
                    break
                await asyncio.sleep(0.05)
                slept += 0.05
        except Exception as e:
            logger.error(f"Error during audio playback: {e}")
        finally:
            sd.stop()
            self.is_playing = False
            logger.info("Finished audio playback.")

    def stop(self):
        if self.is_playing:
            self._stop_event.set()
