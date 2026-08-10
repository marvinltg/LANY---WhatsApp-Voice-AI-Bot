import io
import wave
import logging
import speech_recognition as sr
from datetime import datetime

LOG_FILE = "log.txt"

def _log(message: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [STT-ENGINE] {message}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

logger = logging.getLogger("LANY.STT")

class STTService:
    def __init__(self, language: str = "id-ID"):
        self.language = language
        self.recognizer = sr.Recognizer()

    def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int = 48000, sample_width: int = 2, channels: int = 1) -> str:
        if not pcm_bytes or len(pcm_bytes) < 4800:  # Less than 50ms of audio
            _log(f"Audio terlalu pendek ({len(pcm_bytes) if pcm_bytes else 0} bytes), dilewati.")
            return ""

        _log(f"Menerima {len(pcm_bytes)} bytes PCM audio (sample_rate={sample_rate}, channels={channels})")

        try:
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_bytes)

            wav_io.seek(0)
            _log("WAV container berhasil dibuat, mengirim ke Google STT...")

            with sr.AudioFile(wav_io) as source:
                audio_data = self.recognizer.record(source)

            # Recognize speech using Google STT (Free endpoint)
            transcript = self.recognizer.recognize_google(audio_data, language=self.language)
            _log(f"STT BERHASIL → '{transcript}'")
            logger.info(f"[STT RESULT] '{transcript}'")
            print(f"[STT] Suara Penelepon Dikonversi: '{transcript}'")
            return transcript
        except sr.UnknownValueError:
            _log("Google STT tidak mengenali ucapan (mungkin hening atau noise).")
            logger.debug("[STT] Speech not recognized (silence or ambient noise).")
            print("[STT] Suara tidak terdengar jelas / hening.")
            return ""
        except sr.RequestError as e:
            logger.error(f"[STT] API request error: {e}")
            return ""
        except Exception as e:
            logger.error(f"[STT] Unexpected error: {e}")
            return ""
