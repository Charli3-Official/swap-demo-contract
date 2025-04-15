"""Custom exceptions for blockchain operations."""


class ChainQueryError(Exception):
    """Base exception for chain query errors."""

    pass


class UTxOQueryError(ChainQueryError):
    """Raised when UTxO queries fail."""

    pass


class NetworkConfigError(ChainQueryError):
    """Raised when there are network configuration issues."""

    pass


class NetworkTimeError(ChainQueryError):
    """Raised when there are issues with network time calculations."""

    pass


class ValidationError(ChainQueryError):
    """Base class for validation errors."""

    pass


class TransactionError(ChainQueryError):
    """Base class for transaction related errors."""

    pass


class TransactionSubmissionError(TransactionError):
    """Raised when transaction submission fails."""

    pass


class TransactionConfirmationError(TransactionError):
    """Raised when transaction confirmation fails."""

    pass


class CollateralError(TransactionError):
    """Raised when there are issues with collateral UTxOs."""

    pass


class ChainContextError(ChainQueryError):
    """Raised when there are issues with chain contexts."""

    def __init__(self, message: str = "No valid chain context available") -> None:
        super().__init__(message)


class ScriptQueryError(ChainQueryError):
    """Raised when script queries fail."""

    pass


class StateValidationError(ValidationError):
    """Raised when oracle state validation fails."""

    pass


class OracleError(Exception):
    """Base exception for all oracle-related errors."""

    pass


class ValidationError(OracleError):
    """Base exception for validation errors."""

    pass


class TransactionBuildError(TransactionError):
    """Raised when transaction building fails."""
