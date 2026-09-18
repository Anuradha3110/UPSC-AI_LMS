"""
MOD-05's handwritten-scan intake (Fig. 2's "Handwritten scan -> OCR
extract" path). A dedicated OCR vendor is the real-deployment choice
once volume justifies it; this build uses Claude's own vision input to
transcribe the photographed answer sheet, which is enough for a
functional prototype without standing up a separate OCR service.
"""
import base64

from anthropic import AsyncAnthropic

from app.core.config import settings
from app.services.anthropic_utils import first_text

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def transcribe_handwritten_answer(image_bytes: bytes, media_type: str) -> str:
    client = _get_client()
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Transcribe this photographed handwritten UPSC Mains answer sheet "
                            "exactly as written. Preserve paragraph breaks. Output only the "
                            "transcribed text, no commentary."
                        ),
                    },
                ],
            }
        ],
    )
    return first_text(response).strip()
