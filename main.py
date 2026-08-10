import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level_str, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("LANY.Main")

LOG_FILE = "log.txt"

def call_log(tag: str, message: str):
    """Write log to log.txt and print to terminal."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [{tag}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

from src.browser.chromium import ChromiumManager
from src.browser.whatsapp import WhatsAppController
from src.audio.capture import AudioCapturer
from src.audio.playback import AudioPlayer
from src.audio.vad import VAD
from src.stt.service import STTService
from src.ai.groq_engine import GroqClient
from src.ai.prompt_builder import load_ai_config
from src.tts.service import TTSService
from src.session.manager import SessionManager, CallState


async def calibrate_noise_floor(capturer: AudioCapturer, vad: VAD, duration_secs: float = 2.5):
    """
    Capture silence for `duration_secs` seconds to measure noise floor.
    Call this BEFORE playing the greeting so caller hasn't spoken yet.
    """
    call_log("AUDIO", f"Calibration started ({duration_secs}s noise sampling)...")

    # Drain any existing audio in buffer first
    await capturer.get_audio_chunk()

    # Collect audio over the calibration period
    collected = bytearray()
    tick = 0.1  # sample every 100ms
    elapsed = 0.0
    while elapsed < duration_secs:
        await asyncio.sleep(tick)
        chunk = await capturer.get_audio_chunk()
        if chunk:
            collected.extend(chunk)
        elapsed += tick

    if len(collected) < 1000:
        call_log("AUDIO", "Calibration: not enough data captured. Using default noise floor.")
        return

    noise_floor, threshold = vad.calibrate(bytes(collected))
    call_log("AUDIO", f"Noise floor: {noise_floor:.1f} dBFS")
    call_log("AUDIO", f"Speech threshold: {threshold:.1f} dBFS  (margin={vad.margin_db:.1f} dB)")
    call_log("AUDIO", "Listening...")


async def run_LANY():
    call_log("SYSTEM", "=========================================")
    call_log("SYSTEM", "   Starting LANY WhatsApp Voice AI Bot   ")
    call_log("SYSTEM", "=========================================")

    # --- Load config ---
    ai_config = load_ai_config()
    greeting_text = ai_config.get("voice_behavior", {}).get(
        "greeting",
        "Haiii, hopeless romantic kenapa nelfon"
    )

    input_device = os.getenv("AUDIO_INPUT_DEVICE")
    output_device = os.getenv("AUDIO_OUTPUT_DEVICE")
    call_log("AUDIO", f"Input device: '{input_device}'")
    call_log("AUDIO", f"Output device: '{output_device}'")

    # --- VAD config from .env ---
    vad_margin_db      = float(os.getenv("VAD_MARGIN_DB", "15"))
    vad_min_speech_ms  = int(os.getenv("VAD_MIN_SPEECH_MS", "250"))
    vad_hangover_ms    = int(os.getenv("VAD_SILENCE_HANGOVER_MS", "800"))
    vad_calib_secs     = float(os.getenv("VAD_CALIBRATION_SECS", "2.5"))
    audio_debug        = os.getenv("AUDIO_DEBUG", "false").lower() == "true"
    post_tts_settle_ms = int(os.getenv("POST_TTS_SETTLE_MS", "500"))

    call_log("VAD", f"Config: margin={vad_margin_db}dB  min_speech={vad_min_speech_ms}ms  hangover={vad_hangover_ms}ms  debug={audio_debug}")
    call_log("VAD", f"Post-TTS settle: {post_tts_settle_ms}ms")

    async def flush_and_settle():
        """
        After TTS playback finishes:
        1. Drain stale audio accumulated during TTS (echo)
        2. Wait for audio pipeline to settle
        3. Reset VAD state machine to SILENCE
        Then caller can speak and be heard cleanly.
        """
        call_log("TTS-GUARD", "TTS finished")
        call_log("TTS-GUARD", "Flushing stale audio buffer (TTS echo)")
        # Drain up to 4 ticks of accumulated audio so echo doesn't enter VAD
        for _ in range(4):
            await capturer.get_audio_chunk()
            await asyncio.sleep(0.05)
        call_log("TTS-GUARD", f"Waiting {post_tts_settle_ms}ms for audio pipeline to settle")
        await asyncio.sleep(post_tts_settle_ms / 1000.0)
        vad.reset()
        call_log("TTS-GUARD", "VAD reset to SILENCE")
        call_log("TTS-GUARD", "Caller listening resumed")

    # --- Initialize services ---
    capturer = AudioCapturer(device_name=input_device)
    player   = AudioPlayer(device_name=output_device)
    vad      = VAD(
        sample_rate=48000,
        margin_db=vad_margin_db,
        min_speech_ms=vad_min_speech_ms,
        silence_hangover_ms=vad_hangover_ms,
        debug=audio_debug,
    )
    stt      = STTService()
    ai_engine = GroqClient()
    tts      = TTSService()
    session  = SessionManager()

    # --- Launch Chromium ---
    browser_mgr   = ChromiumManager()
    page          = await browser_mgr.start()
    wa_controller = WhatsAppController(page)

    await wa_controller.open_whatsapp()
    call_log("SYSTEM", "LANY is now monitoring for incoming WhatsApp calls...")

    call_alive_cooldown = 0
    status_tick = 0  # counter for periodic status print

    try:
        while True:
            await asyncio.sleep(0.1)  # tight loop for responsive VAD
            status_tick += 1

            # ----------------------------------------------------------------
            # IDLE: wait for incoming call
            # ----------------------------------------------------------------
            if session.get_state() == CallState.IDLE.value:
                # Only check for calls every 1s to avoid hammering the DOM
                if status_tick % 10 == 0:
                    has_call = await wa_controller.check_incoming_call()
                    if has_call:
                        call_log("CALL", "Incoming call detected!")
                        session.start_session(caller_info="WhatsApp Penelepon")
                        session.update_state(CallState.CONNECTING)

                        answered = await wa_controller.answer_call()
                        if answered:
                            call_log("CALL", "Call answered. Waiting for WebRTC connection...")
                            await asyncio.sleep(2)
                            session.update_state(CallState.CONNECTED)

                            # Start capture
                            capturer.start_capture()
                            call_log("AUDIO", f"Audio capture started on device index {capturer.device_idx}")

                            # Calibrate noise floor BEFORE playing greeting
                            await calibrate_noise_floor(capturer, vad, duration_secs=vad_calib_secs)

                            # Play greeting
                            call_log("LANY", f"Greeting: '{greeting_text}'")
                            session.update_state(CallState.SPEAKING)
                            greeting_pcm = await tts.synthesize_to_pcm(greeting_text)
                            if greeting_pcm:
                                call_log("TTS-GUARD", "LANY speaking — VAD/STT input processing paused")
                                call_log("TTS", f"Playing greeting ({len(greeting_pcm)} bytes PCM)")
                                await player.play_pcm_data(greeting_pcm)
                            session.add_history("model", greeting_text)

                            await flush_and_settle()
                            session.update_state(CallState.LISTENING)
                            call_alive_cooldown = 150  # 15s cooldown (150 ticks x 0.1s)
                            call_log("CALL", "LANY listening. Call monitoring cooldown 15s active.")
                        else:
                            call_log("CALL", "Failed to answer call automatically.")
                            session.end_session()

            # ----------------------------------------------------------------
            # ACTIVE CALL
            # ----------------------------------------------------------------
            elif session.get_state() in [
                CallState.CONNECTED.value,
                CallState.LISTENING.value,
                CallState.PROCESSING.value,
                CallState.SPEAKING.value,
            ]:
                # Call alive check (skip during cooldown)
                if call_alive_cooldown > 0:
                    call_alive_cooldown -= 1
                elif status_tick % 20 == 0:  # check every 2s
                    is_active = await wa_controller.check_call_active()
                    if not is_active:
                        call_log("CALL", "Call ended (caller hung up or WhatsApp timeout).")
                        capturer.stop_capture()
                        player.stop()
                        call_alive_cooldown = 0
                        session.update_state(CallState.DISCONNECTED)
                        session.end_session()
                        session.update_state(CallState.IDLE)
                        continue

                # ---- VAD processing (only when LISTENING) ----
                if session.get_state() == CallState.LISTENING.value:
                    pcm_chunk = await capturer.get_audio_chunk()
                    if not pcm_chunk:
                        continue

                    # Periodic raw dB status line (every ~500ms = 5 ticks of 100ms)
                    if status_tick % 5 == 0:
                        # Compute dB of latest chunk
                        import numpy as np
                        data = np.frombuffer(pcm_chunk, dtype=np.int16).astype(np.float32)
                        rms = float(np.sqrt(np.mean(data ** 2))) if len(data) > 0 else 0
                        db = 20 * np.log10(rms / 32768.0) if rms > 0 else -96.0
                        print(
                            f"[AUDIO] dBFS={db:.1f}  "
                            f"noise_floor={vad.noise_floor_db:.1f}  "
                            f"threshold={vad.threshold_db:.1f}  "
                            f"state={vad.state.value}",
                            end="\r"
                        )

                    # Run through VAD state machine
                    completed_segments = vad.process(pcm_chunk)

                    for segment in completed_segments:
                        duration_s = len(segment) / (48000 * 2)
                        call_log("VAD", f"Speech segment ready: {duration_s:.2f}s  {len(segment)} bytes")

                        session.update_state(CallState.PROCESSING)
                        call_log("STT", f"Sending {len(segment)} bytes to Speech-to-Text...")

                        transcript = await asyncio.to_thread(stt.transcribe_pcm, segment)
                        call_log("STT", f"Transcript: '{transcript}'")

                        if transcript:
                            session.add_history("user", transcript)

                            call_log("GROQ", f"Sending to Groq: '{transcript}'")
                            history = session.get_history()
                            lany_reply = await ai_engine.generate_response(transcript, history[:-1])
                            call_log("GROQ", f"LANY reply: '{lany_reply}'")

                            if lany_reply:
                                session.update_state(CallState.SPEAKING)
                                session.add_history("model", lany_reply)
                                pcm_reply = await tts.synthesize_to_pcm(lany_reply)
                                if pcm_reply:
                                    call_log("TTS-GUARD", "LANY speaking — VAD/STT input processing paused")
                                    call_log("TTS", f"Playing reply ({len(pcm_reply)} bytes PCM)")
                                    await player.play_pcm_data(pcm_reply)
                                    await flush_and_settle()
                        else:
                            call_log("STT", "No speech recognized from segment.")

                        session.update_state(CallState.LISTENING)

    except KeyboardInterrupt:
        call_log("SYSTEM", "Shutdown by user (Ctrl+C).")
        logger.info("Keyboard interrupt received. Shutting down LANY...")
    except Exception as e:
        call_log("ERROR", f"Fatal exception: {e}")
        logger.critical(f"Fatal unhandled exception: {e}", exc_info=True)
    finally:
        capturer.stop_capture()
        player.stop()
        await browser_mgr.stop()
        call_log("SYSTEM", "LANY shutdown complete.")
        logger.info("LANY shutdown complete.")


if __name__ == "__main__":
    asyncio.run(run_LANY())
