from django.test import override_settings

from apps.ai.providers import FakeAIProvider, get_ai_provider


def test_fake_provider_returns_deterministic_embeddings():
    provider = FakeAIProvider(dimensions=16)

    first = provider.embed_text("reset password")
    second = provider.embed_text("reset password")

    assert first == second
    assert len(first) == 16


def test_fake_provider_returns_different_embeddings_for_different_text():
    provider = FakeAIProvider(dimensions=16)

    first = provider.embed_text("reset password")
    second = provider.embed_text("billing issue")

    assert first != second


@override_settings(AI_PROVIDER="fake", FAKE_EMBEDDING_DIMENSIONS=8)
def test_provider_factory_returns_fake_provider():
    provider = get_ai_provider()

    assert isinstance(provider, FakeAIProvider)
    assert provider.embedding_dimensions == 8
