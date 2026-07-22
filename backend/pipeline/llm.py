from typing import Optional

from anthropic import AsyncAnthropic

from config import settings

_client: Optional[AsyncAnthropic] = None

LANGUAGE_NAMES = {"ur": "Urdu", "en": "English", "hi": "Hindi"}

SYSTEM_PROMPT = """You are a kind, patient, and clear tech assistant helping a user navigate their device. You are shown a screenshot of what the user currently sees.

The user's preferred language is: {LANGUAGE}

RULES:
- Respond ONLY in {LANGUAGE}. Do not switch to English unless {LANGUAGE} is English.
- Give a maximum of 3 steps. Do not overwhelm.
- Keep each step to one short sentence, ending with a period.
- Reference visible UI elements by their exact on-screen label or colour/position.
- Use simple, non-technical language a grandparent would understand.
- If you cannot identify the screen, say so and ask the user to describe what they see.
- Never mention AI, models, APIs, or any technical internals.
- Never use markdown formatting, bold (**), bullet points, or special characters. Respond in plain text only.
- Never say you cannot help. Always attempt guidance or ask a clarifying question.

PREVIOUS CONTEXT (last 3 exchanges):
{SESSION_CONTEXT}"""


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        kwargs: dict = {"api_key": settings.anthropic_api_key}
        if settings.anthropic_base_url:
            kwargs["base_url"] = settings.anthropic_base_url
            # Some reseller gateways only accept requests that identify as the
            # Claude Code CLI and reject the SDK's default User-Agent.
            kwargs["default_headers"] = {"User-Agent": "claude-cli/1.0.83 (external, cli)"}
        _client = AsyncAnthropic(**kwargs)
    return _client


def build_prompt(language: str, session_context: list[dict]) -> str:
    language_name = LANGUAGE_NAMES.get(language, "English")
    context_str = "\n".join(
        [f"User: {e['user']}\nAssistant: {e['assistant']}" for e in session_context]
    ) if session_context else "No previous context."
    return SYSTEM_PROMPT.format(
        LANGUAGE=language_name,
        SESSION_CONTEXT=context_str,
    )


async def stream_guidance(
    screenshot_base64: str,
    user_query: str,
    language: str,
    session_context: list[dict],
):
    client = _get_client()
    system_prompt = build_prompt(language, session_context)
    language_name = LANGUAGE_NAMES.get(language, "English")
    # Non-streaming call. Anthropic-compatible resellers (e.g. agentrouter ->
    # Bedrock) emit SSE events with extra/null fields that newer versions of the
    # Anthropic SDK's streaming parser silently drop, yielding an empty
    # text_stream on an HTTP 200. messages.create() reads the final content[]
    # array instead and is unaffected by those non-standard stream events.
    message = await client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": screenshot_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"The user asked: '{user_query}'. Respond in {language_name} "
                            "with at most 3 simple steps referencing what you see on the screen."
                        ),
                    },
                ],
            }
        ],
    )
    text = "".join(
        getattr(block, "text", "") for block in message.content if getattr(block, "type", None) == "text"
    )
    if text:
        yield text
