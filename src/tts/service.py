import os
import io
import re
import asyncio
import logging
import tempfile
from scipy.io import wavfile
import numpy as np
import imageio_ffmpeg
from elevenlabs.client import ElevenLabs

logger = logging.getLogger("LANY.TTS")

class TTSService:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "Pq1mYZe3vRvysasMNyaJ")
        timeout_str = os.getenv("ELEVENLABS_TIMEOUT", "15")
        try:
            self.timeout = float(timeout_str)
        except ValueError:
            self.timeout = 15.0

        if not self.api_key:
            logger.warning("[TTS] ELEVENLABS_API_KEY is not set. TTS may fail if API key is required.")
        
        logger.info(f"[TTS] Provider: ElevenLabs (Official SDK)")
        logger.info(f"[TTS] Voice ID: {self.voice_id}")
        logger.info(f"[TTS] Model: eleven_v3")
        logger.info(f"[TTS] Output format: mp3_44100_128")
        
        self.client = ElevenLabs(
            api_key=self.api_key or "",
            timeout=self.timeout
        )

    def _cleanup_text(self, text: str) -> str:
        """Remove markdown and excessive symbols that TTS shouldn't read."""
        text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
        text = re.sub(r'_{1,3}(.*?)_{1,3}', r'\1', text)
        text = re.sub(r'`(.*?)`', r'\1', text)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    async def synthesize_to_pcm(self, text: str, target_sample_rate: int = 48000) -> bytes:
        if not text:
            return b""

        clean_text = self._cleanup_text(text)
        if not clean_text:
            return b""

        logger.info(f'[TTS] Synthesizing: "{clean_text[:50]}..."')

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_tmp:
            mp3_path = mp3_tmp.name

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_tmp:
            wav_path = wav_tmp.name

        try:
            # 1. Synthesize with ElevenLabs Official Sync SDK via to_thread
            def _fetch_audio():
                # returns a generator of bytes
                return self.client.text_to_speech.convert(
                    text=clean_text,
                    voice_id=self.voice_id,
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128"
                )

            audio_generator = await asyncio.to_thread(_fetch_audio)
            
            # Consume the generator to get full mp3 bytes
            def _consume_generator(gen):
                return b"".join(gen)

            audio_bytes = await asyncio.to_thread(_consume_generator, audio_generator)
            logger.info("[TTS] ElevenLabs audio received")

            # Save the raw output (mp3) to a file
            with open(mp3_path, "wb") as f:
                f.write(audio_bytes)

            # 2. Convert MP3 to WAV using imageio-ffmpeg binary
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            proc = await asyncio.create_subprocess_exec(
                ffmpeg_exe, "-y", "-i", mp3_path,
                "-ar", str(target_sample_rate),
                "-ac", "1",
                "-f", "wav",
                wav_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.communicate()
            logger.info("[TTS] MP3 decoded")

            # 3. Read generated WAV file into raw 16-bit PCM bytes
            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                sample_rate, data = wavfile.read(wav_path)
                if data.dtype != np.int16:
                    # Normalize float or int32 to int16
                    data = (data / np.max(np.abs(data)) * 32767).astype(np.int16)
                pcm_bytes = data.tobytes()
                logger.info(f"[TTS] PCM converted")
                logger.info(f"[TTS] Sending audio to virtual microphone (Size: {len(pcm_bytes)} bytes)")
                return pcm_bytes
            else:
                logger.error("[TTS ERROR] Failed to generate PCM audio via ffmpeg.")
                return b""
        except Exception as e:
            logger.error(f"[TTS ERROR] ElevenLabs synthesis failed: {e}")
            return b""
        finally:
            # Cleanup temp files
            for p in [mp3_path, wav_path]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
