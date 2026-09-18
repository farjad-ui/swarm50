class LedgerError(Exception):
    """Base class for all budget-enforcement errors."""


class WalletEmpty(LedgerError):
    pass


class CycleCapExceeded(LedgerError):
    pass


class StakeCapExceeded(LedgerError):
    pass


class UnknownModel(LedgerError):
    pass


class BackendError(Exception):
    """The model backend (SDK or CLI) failed before any usage could be trusted. Nothing was debited."""
