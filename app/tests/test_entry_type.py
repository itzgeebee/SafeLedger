"""
Unit tests for domain layer - Entry Type enum.
"""

import pytest

from app.domain.entry_type import EntryType


class TestEntryType:
    def test_debit_value(self):
        """DEBIT should have correct value."""
        assert EntryType.DEBIT.value == "DEBIT"

    def test_credit_value(self):
        """CREDIT should have correct value."""
        assert EntryType.CREDIT.value == "CREDIT"

    def test_debit_opposite(self):
        """DEBIT opposite should be CREDIT."""
        assert EntryType.DEBIT.opposite() == EntryType.CREDIT

    def test_credit_opposite(self):
        """CREDIT opposite should be DEBIT."""
        assert EntryType.CREDIT.opposite() == EntryType.DEBIT

    def test_entry_type_is_string(self):
        """EntryType should be usable as string."""
        assert EntryType.DEBIT == "DEBIT"
        assert EntryType.CREDIT == "CREDIT"

    def test_entry_type_from_string(self):
        """Should be constructable from string."""
        assert EntryType("DEBIT") == EntryType.DEBIT
        assert EntryType("CREDIT") == EntryType.CREDIT

    def test_invalid_entry_type_raises(self):
        """Invalid value should raise ValueError."""
        with pytest.raises(ValueError):
            EntryType("INVALID")
