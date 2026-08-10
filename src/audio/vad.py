import os
import wave
import logging
import numpy as np
from enum import Enum
from datetime import datetime

logger = logging.getLogger("LANY.VAD")

LOG_FILE = "log.txt"

def _vad_log(message: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [VAD] {message}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


class VADState(Enum):
    SILENCE = "SILENCE"
    POSSIBLE_SPEECH = "POSSIBLE_SPEECH"
    SPEAKING = "SPEAKING"
    POSSIBLE_SILENCE = "POSSIBLE_SILENCE"


class VAD:
    """
    Voice Activity Detector with:
    - Noise floor calibration
    - Relative speech threshold (noise_floor + margin)
    - Minimum speech duration guard
    - Silence hangover (grace period before declaring end-of-speech)
    - Optional debug WAV output
    """

    # Analysis window: 50ms per sub-chunk
    ANALYSIS_MS = 50

    def __init__(
        self,
        sample_rate: int = 48000,
        margin_db: float = 15.0,
        min_speech_ms: int = 250,
        silence_hangover_ms: int = 800,
        debug: bool = False,
    ):
        self.sample_rate = sample_rate
        self.margin_db = margin_db
        self.min_speech_ms = min_speech_ms
        self.silence_hangover_ms = silence_hangover_ms
        self.debug = debug

        # Calibration results
        self.noise_floor_db: float = -90.0
        self.threshold_db: float = -90.0 + margin_db
        self.calibrated: bool = False

        # State machine
        self.state = VADState.SILENCE
        self.speech_buffer = bytearray()
        self._possible_speech_ticks = 0
        self._possible_silence_ticks = 0
        self._debug_counter = 0

        # Sub-chunk size in bytes (50ms, 16-bit mono)
        self._analysis_bytes = int(sample_rate * (self.ANALYSIS_MS / 1000.0)) * 2

        # How many consecutive 50ms windows of speech needed to confirm SPEAKING
        self._min_speech_ticks = max(1, int(min_speech_ms / self.ANALYSIS_MS))

        # How many consecutive 50ms windows of silence = end-of-speech
        self._silence_hangover_ticks = max(1, int(silence_hangover_ms / self.ANALYSIS_MS))

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(self, pcm_bytes: bytes):
        """
        Compute noise floor from a buffer assumed to be silence.
        Uses 75th percentile of measured dB values for robustness.
        """
        db_values = []
        step = self._analysis_bytes
        for i in range(0, len(pcm_bytes) - step, step):
            chunk = pcm_bytes[i : i + step]
            db = self._db(chunk)
            if db > -96.0:
                db_values.append(db)

        if not db_values:
            _vad_log("Calibration failed: no valid audio chunks.")
            return self.noise_floor_db, self.threshold_db

        # Log all samples
        _vad_log("Calibration samples:")
        for v in db_values:
            _vad_log(f"  {v:.1f} dBFS")

        # Use 75th percentile to avoid outlier spikes counting as noise
        self.noise_floor_db = float(np.percentile(db_values, 75))
        self.threshold_db = self.noise_floor_db + self.margin_db
        self.calibrated = True

        _vad_log(f"Noise floor: {self.noise_floor_db:.1f} dBFS")
        _vad_log(f"Speech threshold: {self.threshold_db:.1f} dBFS  (margin={self.margin_db:.1f} dB)")
        return self.noise_floor_db, self.threshold_db

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self, pcm_bytes: bytes) -> list[bytes]:
        """
        Feed a chunk of PCM audio into the VAD.
        Returns a list of completed speech segments (each as bytes).
        Each segment is ready to be sent to STT.
        """
        completed_segments = []
        step = self._analysis_bytes

        for i in range(0, len(pcm_bytes), step):
            sub_chunk = pcm_bytes[i : i + step]
            if len(sub_chunk) < step // 4:
                continue

            db = self._db(sub_chunk)
            is_speech = db > self.threshold_db

            # Periodic status log (every ~500ms = every 10 ticks of 50ms)
            # We'll let main.py do periodic prints; here just log transitions.

            segment = self._tick(sub_chunk, db, is_speech)
            if segment:
                completed_segments.append(segment)

        return completed_segments

    def get_status_line(self, db: float) -> str:
        """Return a formatted one-line status for display."""
        return (
            f"dBFS={db:.1f}  "
            f"noise_floor={self.noise_floor_db:.1f}  "
            f"threshold={self.threshold_db:.1f}  "
            f"state={self.state.value}"
        )

    # ------------------------------------------------------------------
    # Internal state machine
    # ------------------------------------------------------------------

    def _tick(self, chunk: bytes, db: float, is_speech: bool) -> bytes | None:
        """One 50ms tick through the state machine. Returns segment if ended."""

        if self.state == VADState.SILENCE:
            if is_speech:
                self.state = VADState.POSSIBLE_SPEECH
                self._possible_speech_ticks = 1
                self.speech_buffer = bytearray(chunk)

        elif self.state == VADState.POSSIBLE_SPEECH:
            if is_speech:
                self._possible_speech_ticks += 1
                self.speech_buffer.extend(chunk)
                if self._possible_speech_ticks >= self._min_speech_ticks:
                    self.state = VADState.SPEAKING
                    duration_so_far = (len(self.speech_buffer) / 2) / self.sample_rate
                    _vad_log(
                        f"Speech segment started  "
                        f"dBFS={db:.1f}  noise_floor={self.noise_floor_db:.1f}  "
                        f"threshold={self.threshold_db:.1f}"
                    )
            else:
                # False trigger — discard
                self.state = VADState.SILENCE
                self.speech_buffer.clear()
                self._possible_speech_ticks = 0

        elif self.state == VADState.SPEAKING:
            self.speech_buffer.extend(chunk)
            if not is_speech:
                self.state = VADState.POSSIBLE_SILENCE
                self._possible_silence_ticks = 1
                _vad_log(
                    f"dBFS={db:.1f}  noise_floor={self.noise_floor_db:.1f}  "
                    f"threshold={self.threshold_db:.1f}  state=POSSIBLE_SILENCE"
                )

        elif self.state == VADState.POSSIBLE_SILENCE:
            self.speech_buffer.extend(chunk)
            if is_speech:
                # Still speaking
                self.state = VADState.SPEAKING
                self._possible_silence_ticks = 0
            else:
                self._possible_silence_ticks += 1
                if self._possible_silence_ticks >= self._silence_hangover_ticks:
                    # Speech ended
                    duration_s = len(self.speech_buffer) / (self.sample_rate * 2)
                    _vad_log(f"Speech segment ended  Duration: {duration_s:.2f}s  Size: {len(self.speech_buffer)} bytes")

                    segment = bytes(self.speech_buffer)
                    self.speech_buffer.clear()
                    self.state = VADState.SILENCE
                    self._possible_silence_ticks = 0
                    self._possible_speech_ticks = 0

                    if self.debug and segment:
                        self._save_debug_wav(segment)

                    return segment

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _db(self, pcm_bytes: bytes) -> float:
        if not pcm_bytes:
            return -96.0
        data = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
        if len(data) == 0:
            return -96.0
        rms = np.sqrt(np.mean(data ** 2))
        if rms <= 0:
            return -96.0
        return float(20 * np.log10(rms / 32768.0))

    def reset(self):
        """
        Reset the VAD state machine to SILENCE.
        Call this after TTS finishes to discard any accumulated echo.
        Calibration data (noise_floor, threshold) is preserved.
        """
        self.state = VADState.SILENCE
        self.speech_buffer.clear()
        self._possible_speech_ticks = 0
        self._possible_silence_ticks = 0

    def _save_debug_wav(self, pcm_bytes: bytes):
        os.makedirs("temp/debug", exist_ok=True)
        self._debug_counter += 1
        filename = f"temp/debug/caller_{self._debug_counter:03d}.wav"
        try:
            with wave.open(filename, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(pcm_bytes)
            _vad_log(f"Debug WAV saved: {filename}")
        except Exception as e:
            logger.error(f"[VAD] Failed to save debug WAV: {e}")
