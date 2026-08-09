import os
import logging
from google import genai
from google.genai import types
from src.ai.prompt_builder import build_system_instruction
from src.ai.security import sanitize_input

logger = logging.getLogger("LANY.Gemini")

class GeminiClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("GEMINI_API_KEY is not set in environment or arguments!")
            raise ValueError("GEMINI_API_KEY is required.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.system_instruction = build_system_instruction()

    async def generate_response(self, transcript: str, history: list[dict] = None) -> str:
        clean_transcript = sanitize_input(transcript)
        if not clean_transcript:
            return ""

        logger.info(f"[GEMINI INPUT] User said: '{clean_transcript}'")

        # Format history into contents if available
        contents = []
        if history:
            for item in history:
                role = "user" if item.get("role") == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=item.get("text", ""))]
                ))

        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=clean_transcript)]
        ))

        try:
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.7,
                max_output_tokens=150
            )

            # Request response using gemini-2.5-flash or gemini-1.5-flash model
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config
            )

            reply_text = response.text.strip() if response.text else ""
            logger.info(f"[GEMINI OUTPUT] LANY response: '{reply_text}'")
            return reply_text
        except Exception as e:
            logger.error(f"[GEMINI ERROR] Failed to generate response: {e}")
            return "Maaf ya sayang, koneksiku agak sedikit terganggu tadi."
