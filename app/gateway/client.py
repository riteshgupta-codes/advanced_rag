import logfire
from portkey_ai import Portkey, createHeaders, PORTKEY_GATEWAY_URL
from langchain_openai import ChatOpenAI

from app.config import settings


# Portkey gateway configuration.
# Primary and fallback both use a model currently accessible
# through the user's Groq account.
GATEWAY_CONFIG = {
    "strategy": {"mode": "fallback"},
    "cache": {"mode": "simple"},
    "retry": {
        "attempts": 2,
        "on_status_codes": [429, 503]
    },
    "targets": [
        {
            "override_params": {
                "model": f"@{settings.GROQ_SLUG}/openai/gpt-oss-20b"
            }
        },
        {
            "override_params": {
                "model": f"@{settings.GROQ_SLUG_2}/openai/gpt-oss-20b"
            }
        },
    ]
}


# Use the saved Portkey Config.
portkey_client = Portkey(
    api_key=settings.PORTKEY_API_KEY,
    config=settings.PORTKEY_CONFIG_SLUG
)


def get_langchain_llm(feature: str = "rag") -> ChatOpenAI:
    """
    Return a Portkey-backed ChatOpenAI instance.

    LangChain talks to Portkey through the OpenAI-compatible API.
    Portkey then routes the request to the configured Groq provider.
    """

    return ChatOpenAI(
        api_key=settings.PORTKEY_API_KEY,
        base_url=PORTKEY_GATEWAY_URL,
        model=f"@{settings.GROQ_SLUG}/openai/gpt-oss-20b",
        temperature=0,
        default_headers=createHeaders(
            api_key=settings.PORTKEY_API_KEY,
            config=settings.PORTKEY_CONFIG_SLUG,
            metadata={
                "feature": feature,
                "_user": "rag-system",
                "environment": "production"
            }
        )
    )


def extract_cache_status(response) -> str:
    """
    Extract Portkey cache status from the response headers.

    Returns:
        HIT, MISS, or MISS if the header cannot be found.
    """

    for attr in ("_raw_response", "_response", "_http_response"):
        raw = getattr(response, attr, None)

        if raw is not None:
            headers = getattr(raw, "headers", {})
            status = headers.get("x-portkey-cache-status", "")

            if status:
                return status.upper()

    return "MISS"