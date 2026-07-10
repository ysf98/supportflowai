class AIProviderError(Exception):
    """Raised when an AI provider cannot complete a request safely."""


class AIProviderConfigurationError(AIProviderError):
    """Raised when a provider is missing required configuration."""
