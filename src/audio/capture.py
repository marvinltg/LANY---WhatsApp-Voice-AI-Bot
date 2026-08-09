import asyncio
import sounddevice as sd
import numpy as np
import logging
from src.audio.devices import find_device_index, get_audio_config
from src.audio.buffer import AudioBuffer

logger = logging.getLogger("LANY.AudioCapture")

class AudioCapturer:
    def __init__(self, device_name: str | None = None):
        self.config = get_audio_config()
        self.device_idx = find_device_index(device_name, is_input=True) if device_name else None
        self.buffer = AudioBuffer(sample_rate=self.config["sample_rate"])
        self.stream = None
        self.is_capturing = False
        self.loop = None

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio capture status flag: {status}")
        if self.is_capturing and self.loop:
            # Convert float/int16 PCM bytes
            raw_bytes = indata.tobytes()
            asyncio.run_coroutine_threadsafe(self.buffer.write(raw_bytes), self.loop)

    def start_capture(self):
        if self.is_capturing:
            return
        
        self.loop = asyncio.get_running_loop()
        self.is_capturing = True

        self.stream = sd.InputStream(
            device=self.device_idx,
            channels=self.config["channels"],
            samplerate=self.config["sample_rate"],
            dtype=self.config["dtype"],
            callback=self._audio_callback,
            blocksize=2400 # 50ms chunks at 48kHz
        )
        self.stream.start()
        logger.info(f"Started audio capture on device index {self.device_idx}")

    def stop_capture(self):
        if not self.is_capturing:
            return
        self.is_capturing = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        logger.info("Stopped audio capture.")

    async def get_audio_chunk(self) -> bytes:
        return await self.buffer.read_all()
