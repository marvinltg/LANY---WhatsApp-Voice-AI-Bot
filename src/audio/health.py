import numpy as np
import logging

logger = logging.getLogger("LANY.AudioHealth")

class AudioHealthMonitor:
    @staticmethod
    def calculate_db(pcm_bytes: bytes) -> float:
        if not pcm_bytes:
            return -96.0  # Silence
        
        data = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
        if len(data) == 0:
            return -96.0

        rms = np.sqrt(np.mean(data**2))
        if rms <= 0:
            return -96.0

        db = 20 * np.log10(rms / 32768.0)
        return float(db)

    @classmethod
    def log_input_level(cls, pcm_bytes: bytes):
        db = cls.calculate_db(pcm_bytes)
        # Tampilkan level input secara langsung supaya kelihatan angkanya
        print(f"🔈 [AUDIO LEVEL] Input dB: {db:.2f}")
        if db > -60.0:
            logger.info(f"[AUDIO HEALTH] Signal detected! Level: {db:.2f} dB")
