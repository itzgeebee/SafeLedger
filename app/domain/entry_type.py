"""
Entry type enum for type-safe ledger operations.
"""

from enum import Enum


class EntryType(str, Enum):
    """
    Ledger entry type: DEBIT or CREDIT.
    Using str mixin for JSON serialization compatibility.
    """

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

    def opposite(self) -> "EntryType":
        """Return the opposite entry type for reversals."""
        return EntryType.CREDIT if self == EntryType.DEBIT else EntryType.DEBIT
