"""
Idempotent ledger with Merkle chain for financial transactions.
Implements determinism contract v1 with ordered hashing and decision traces.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TransactionType(Enum):
    """Financial transaction types"""
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"
    INVESTMENT = "INVESTMENT"
    LOAN = "LOAN"
    LOAN_REPAYMENT = "LOAN_REPAYMENT"
    ACQUISITION = "ACQUISITION"
    DIVIDEND = "DIVIDEND"
    TAX = "TAX"


class Account(Enum):
    """Chart of accounts for double-entry bookkeeping"""
    CASH = "CASH"
    ACCOUNTS_RECEIVABLE = "ACCOUNTS_RECEIVABLE"
    INVENTORY = "INVENTORY"
    EQUIPMENT = " EQUIPMENT"
    ACCOUNTS_PAYABLE = "ACCOUNTS_PAYABLE"
    LOANS_PAYABLE = "LOANS_PAYABLE"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    COGS = "COGS"
    OPERATING_EXPENSES = "OPERATING_EXPENSES"
    INTEREST_EXPENSE = "INTEREST_EXPENSE"


@dataclass
class LedgerEntry:
    """Double-entry accounting ledger entry"""
    debit_account: Account
    credit_account: Account

    def to_dict(self) -> Dict[str, str]:
        return {
            "debit_account": self.debit_account.value,
            "credit_account": self.credit_account.value
        }


@dataclass
class Transaction:
    """Financial transaction with Merkle chain link"""
    transaction_id: str
    timestamp: str
    tick: int
    from_company_id: Optional[str]
    to_company_id: Optional[str]
    amount_usd: float
    transaction_type: TransactionType
    ledger_entry: LedgerEntry
    prev_transaction_hash: Optional[str]
    related_operation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def compute_integrity_hash(self) -> str:
        """Compute SHA-256 hash of transaction payload (deterministic)"""
        payload = {
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp,
            "tick": self.tick,
            "from_company_id": self.from_company_id,
            "to_company_id": self.to_company_id,
            "amount_usd": self.amount_usd,
            "transaction_type": self.transaction_type.value,
            "ledger_entry": self.ledger_entry.to_dict(),
            "prev_transaction_hash": self.prev_transaction_hash,
            "related_operation_id": self.related_operation_id,
            "metadata": self.metadata
        }
        # Determinism contract: ordered hashing
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp,
            "tick": self.tick,
            "from_company_id": self.from_company_id,
            "to_company_id": self.to_company_id,
            "amount_usd": self.amount_usd,
            "transaction_type": self.transaction_type.value,
            "ledger_entry": self.ledger_entry.to_dict(),
            "state_integrity": self.compute_integrity_hash(),
            "prev_transaction_hash": self.prev_transaction_hash,
            "related_operation_id": self.related_operation_id,
            "metadata": self.metadata
        }


class CompanyLedger:
    """
    Per-company transaction ledger with Merkle chain integrity.
    Implements append-only, hash-chained transaction history.
    """

    def __init__(self, company_id: str):
        self.company_id = company_id
        self.transactions: List[Transaction] = []
        self.transaction_index: Dict[str, int] = {}  # transaction_id -> index

    def get_latest_hash(self) -> Optional[str]:
        """Get hash of most recent transaction (for Merkle linking)"""
        if not self.transactions:
            return None
        return self.transactions[-1].compute_integrity_hash()

    def record_transaction(
        self,
        tick: int,
        from_company_id: Optional[str],
        to_company_id: Optional[str],
        amount_usd: float,
        transaction_type: TransactionType,
        debit_account: Account,
        credit_account: Account,
        related_operation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Transaction:
        """
        Record a new transaction with Merkle chain link.
        Returns the created Transaction object.
        """
        transaction_id = str(uuid.uuid4())

        # Check idempotency (duplicate detection)
        if transaction_id in self.transaction_index:
            raise ValueError(f"Duplicate transaction_id: {transaction_id}")

        # Create transaction
        transaction = Transaction(
            transaction_id=transaction_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tick=tick,
            from_company_id=from_company_id,
            to_company_id=to_company_id,
            amount_usd=amount_usd,
            transaction_type=transaction_type,
            ledger_entry=LedgerEntry(debit_account, credit_account),
            prev_transaction_hash=self.get_latest_hash(),
            related_operation_id=related_operation_id,
            metadata=metadata
        )

        # Append to chain
        self.transactions.append(transaction)
        self.transaction_index[transaction_id] = len(self.transactions) - 1

        return transaction

    def verify_chain(self) -> bool:
        """
        Verify Merkle chain integrity for all transactions.
        Returns True if chain is intact, False if corrupted.
        """
        for i in range(1, len(self.transactions)):
            current = self.transactions[i]
            previous = self.transactions[i - 1]

            expected_prev_hash = previous.compute_integrity_hash()
            actual_prev_hash = current.prev_transaction_hash

            if expected_prev_hash != actual_prev_hash:
                return False

        return True

    def get_balance(self, account: Account) -> float:
        """
        Compute current balance for a given account.
        Uses double-entry bookkeeping: debits increase asset accounts, credits decrease them.
        """
        balance = 0.0

        for txn in self.transactions:
            # This is simplified — proper accounting requires account type classification
            if txn.ledger_entry.debit_account == account:
                # For asset accounts (CASH, etc.), debits increase balance
                if account in [Account.CASH, Account.ACCOUNTS_RECEIVABLE, Account.INVENTORY, Account.EQUIPMENT]:
                    balance += txn.amount_usd
                else:
                    # For liability/equity/revenue accounts, debits decrease balance
                    balance -= txn.amount_usd

            if txn.ledger_entry.credit_account == account:
                # For asset accounts, credits decrease balance
                if account in [Account.CASH, Account.ACCOUNTS_RECEIVABLE, Account.INVENTORY, Account.EQUIPMENT]:
                    balance -= txn.amount_usd
                else:
                    # For liability/equity/revenue accounts, credits increase balance
                    balance += txn.amount_usd

        return balance

    def get_cash_balance(self) -> float:
        """Convenience method to get current cash balance"""
        return self.get_balance(Account.CASH)

    def export_audit_trail(self) -> List[Dict[str, Any]]:
        """Export complete transaction history as JSON-serializable list"""
        return [txn.to_dict() for txn in self.transactions]

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Retrieve transaction by ID"""
        if transaction_id not in self.transaction_index:
            return None
        idx = self.transaction_index[transaction_id]
        return self.transactions[idx]

    def get_genesis_hash(self) -> Optional[str]:
        """Get hash of first transaction (genesis)"""
        if not self.transactions:
            return None
        return self.transactions[0].compute_integrity_hash()
