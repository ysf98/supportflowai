import hashlib
from abc import ABC, abstractmethod

from django.conf import settings

from .exceptions import AIProviderConfigurationError, AIProviderError


class BaseAIProvider(ABC):
    name = "base"
    embedding_model = ""
    embedding_dimensions = 0

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]

    @abstractmethod
    def generate_text(self, *, prompt: str, question: str = "", context: str = "") -> str:
        raise NotImplementedError


class FakeAIProvider(BaseAIProvider):
    name = "fake"

    def __init__(self, dimensions: int | None = None):
        self.embedding_dimensions = dimensions or settings.FAKE_EMBEDDING_DIMENSIONS
        self.embedding_model = f"fake-embedding-{self.embedding_dimensions}"

    def embed_text(self, text: str) -> list[float]:
        seed = text.encode("utf-8")
        values = []
        counter = 0

        while len(values) < self.embedding_dimensions:
            digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            for byte in digest:
                values.append((byte / 127.5) - 1.0)
                if len(values) == self.embedding_dimensions:
                    break
            counter += 1

        return values

    def generate_text(self, *, prompt: str, question: str = "", context: str = "") -> str:
        if not context.strip():
            return "I do not have enough information in the available documents to answer this question."

        first_excerpt = ""
        for line in context.splitlines():
            if line.startswith("Excerpt:"):
                first_excerpt = line.replace("Excerpt:", "", 1).strip()
                break

        basis = first_excerpt or context.strip().splitlines()[0]
        return f"Fake answer based on the available documents: {basis}"


class OpenAIProvider(BaseAIProvider):
    name = "openai"

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise AIProviderConfigurationError("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIProviderConfigurationError("The openai package is not installed.") from exc

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        self.embedding_dimensions = settings.SUPPORTFLOW_EMBEDDING_DIMENSIONS

    def embed_text(self, text: str) -> list[float]:
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
                dimensions=self.embedding_dimensions,
            )
        except Exception as exc:
            raise AIProviderError("OpenAI embedding request failed.") from exc

        return response.data[0].embedding

    def generate_text(self, *, prompt: str, question: str = "", context: str = "") -> str:
        chat_model = settings.OPENAI_CHAT_MODEL
        if not chat_model:
            raise AIProviderConfigurationError("OPENAI_CHAT_MODEL is not configured.")

        try:
            response = self.client.chat.completions.create(
                model=chat_model,
                messages=[
                    {"role": "system", "content": "You answer internal support questions using only the supplied context."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
        except Exception as exc:
            raise AIProviderError("OpenAI chat request failed.") from exc

        content = response.choices[0].message.content
        if not content:
            raise AIProviderError("OpenAI returned an empty response.")
        return content.strip()


def get_ai_provider() -> BaseAIProvider:
    provider = settings.AI_PROVIDER.lower()
    if provider == "fake":
        return FakeAIProvider()
    if provider == "openai":
        return OpenAIProvider()
    raise AIProviderConfigurationError(f"Unsupported AI provider: {settings.AI_PROVIDER}")
