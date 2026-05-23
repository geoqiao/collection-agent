class CollectionAgentError(Exception):
    """Base exception for collection agent."""
    pass


class ComplianceViolationError(CollectionAgentError):
    """Raised when compliance check fails."""
    pass


class QuotaExceededError(CollectionAgentError):
    """Raised when quota is exceeded."""
    pass


class ChannelError(CollectionAgentError):
    """Raised when channel operation fails."""
    pass


class StorageError(CollectionAgentError):
    """Raised when storage operation fails."""
    pass
