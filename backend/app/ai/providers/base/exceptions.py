class ProviderError(Exception):
    def __init__(self, message: str, provider: str = "", model: str = "", recoverable: bool = True):
        self.provider = provider
        self.model = model
        self.recoverable = recoverable
        super().__init__(message)


class ProviderUnavailable(ProviderError):
    def __init__(self, provider: str = "", message: str = "Provider is unavailable"):
        super().__init__(message, provider=provider, recoverable=True)


class ModelNotFound(ProviderError):
    def __init__(self, model: str, provider: str = ""):
        super().__init__(f"Model '{model}' not found", provider=provider, model=model, recoverable=True)


class RateLimitExceeded(ProviderError):
    def __init__(self, provider: str = "", retry_after: float = 0.0):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded", provider=provider, recoverable=True)


class ContextTooLarge(ProviderError):
    def __init__(self, provider: str = "", model: str = "", context_length: int = 0):
        self.context_length = context_length
        super().__init__(f"Context too large (max: {context_length})", provider=provider, model=model, recoverable=False)


class InvalidResponse(ProviderError):
    def __init__(self, provider: str = "", message: str = "Invalid response from provider"):
        super().__init__(message, provider=provider, recoverable=False)


class AuthenticationFailed(ProviderError):
    def __init__(self, provider: str = ""):
        super().__init__("Authentication failed", provider=provider, recoverable=False)


class StreamingNotSupported(ProviderError):
    def __init__(self, provider: str = ""):
        super().__init__("Streaming not supported by this provider", provider=provider, recoverable=False)


class ToolCallNotSupported(ProviderError):
    def __init__(self, provider: str = ""):
        super().__init__("Tool calling not supported by this provider", provider=provider, recoverable=False)
