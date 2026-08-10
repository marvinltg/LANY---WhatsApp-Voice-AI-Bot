import os
import re
import logging
import asyncio
from groq import AsyncGroq, APIConnectionError, RateLimitError, APIStatusError
from src.ai.prompt_builder import build_system_instruction
from src.ai.security import sanitize_input

logger = logging.getLogger("LANY.Groq")

FALLBACK_RESPONSE = "Maaf ya, tadi aku agak error. Coba ngomong lagi."


class GroqClient:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

        if not self.api_key:
            logger.warning("[GROQ] GROQ_API_KEY is not set. Requests will fail.")

        logger.info(f"[GROQ] Provider: Groq API")
        logger.info(f"[GROQ] Model: {self.model}")

        self.client = AsyncGroq(api_key=self.api_key or "")
        self.system_instruction = build_system_instruction()

    async def generate_response(self, transcript: str, history: list[dict] = None) -> str:
        clean_transcript = sanitize_input(transcript)
        if not clean_transcript:
            return ""

        logger.info(f"[GROQ] User input: '{clean_transcript}'")

        messages = [
            {"role": "system", "content": self.system_instruction}
        ]

        # Use last 6 turns max to keep latency low and avoid token overflow
        if history:
            for item in history[-6:]:
                role = "user" if item.get("role") == "user" else "assistant"
                content = item.get("text", "")
                if content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": clean_transcript})

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.75,
                max_tokens=120,
                stream=False,
            )

            reply_text = completion.choices[0].message.content or ""
            reply_text = reply_text.strip()

            # Strip any reasoning/thinking block just in case
            reply_text = re.sub(r'<think>.*?</think>', '', reply_text, flags=re.DOTALL).strip()

            if not reply_text:
                logger.warning("[GROQ] Response was empty after cleanup.")
                return FALLBACK_RESPONSE

            logger.info(f"[GROQ] Response: '{reply_text}'")
            return reply_text

        except APIConnectionError:
            logger.error("[GROQ] Connection error. Could not reach Groq API.")
            return FALLBACK_RESPONSE
        except RateLimitError:
            logger.error("[GROQ] Rate limit reached. Slowing down.")
            return FALLBACK_RESPONSE
        except APIStatusError as e:
            logger.error(f"[GROQ] API error {e.status_code}: {e.message}")
            return FALLBACK_RESPONSE
        except asyncio.TimeoutError:
            logger.error("[GROQ] Request timed out.")
            return FALLBACK_RESPONSE
        except Exception as e:
            logger.error(f"[GROQ ERROR] Unexpected error: {e}")
            return FALLBACK_RESPONSE
