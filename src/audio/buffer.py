import asyncio
import numpy as np
import logging

logger = logging.getLogger("LANY.AudioBuffer")

class AudioBuffer:
    def __init__(self, max_seconds: int = 10, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.max_size = max_seconds * sample_rate
        self.buffer = bytearray()
        self._lock = asyncio.Lock()

    async def write(self, data: bytes):
        async with self._lock:
            self.buffer.extend(data)
            # Prevent overflow by truncating oldest samples if exceeds max_size (assuming 16-bit PCM = 2 bytes/sample)
            max_bytes = self.max_size * 2
            if len(self.buffer) > max_bytes:
                self.buffer = self.buffer[-max_bytes:]

    async def read_all(self) -> bytes:
        async with self._lock:
            data = bytes(self.buffer)
            self.buffer.clear()
            return data

    async def clear(self):
        async with self._lock:
            self.buffer.clear()

    async def size_bytes(self) -> int:
        async with self._lock:
            return len(self.buffer)
