"""Core accounting rules for PersonaL Expense Tracker.

Phase 1 deliberately keeps the existing MongoDB records compatible while giving
later phases one canonical vocabulary for transaction classification.
"""

from decimal import Decimal

# Canonical transaction natures. These are business events, not merely cash-flow
# directions. Income and expense affect profit; the other types affect assets or
# liabilities without pretending to be revenue/expense.
TRANSACTION_TYPES = (
    "income",
    "expense",
    "money_lent",
    "money_returned",
    "loan_received",
    "loan_repayment",
    "transfer_in",
    "transfer_out",
    "adjustment",
)

TYPE_LABELS = {
    "income": "Income",
    "expense": "Expense",
    "money_lent": "Money Given",
    "money_returned": "Money Received Back",
    "loan_received": "Loan Received",
    "loan_repayment": "Loan Repayment",
    "transfer_in": "Transfer In",
    "transfer_out": "Transfer Out",
    "adjustment": "Adjustment",
}

# Existing records only have income/expense, so they remain valid forever.
LEGACY_TYPES = {"income", "expense"}

INCOME_TYPES = {"income"}
EXPENSE_TYPES = {"expense"}
RECEIVABLE_TYPES = {"money_lent", "money_returned"}
LIABILITY_TYPES = {"loan_received", "loan_repayment"}
TRANSFER_TYPES = {"transfer_in", "transfer_out"}


def normalize_transaction_type(value, default="expense"):
    """Return a supported canonical transaction type."""
    value = str(value or default).strip().lower()
    aliases = {
        "lent": "money_lent",
        "loan_given": "money_lent",
        "money_given": "money_lent",
        "returned": "money_returned",
        "loan_returned": "money_returned",
        "loan_in": "loan_received",
        "borrowed": "loan_received",
        "loan_out": "loan_repayment",
        "repaid": "loan_repayment",
        "transfer": "transfer_out",
    }
    value = aliases.get(value, value)
    return value if value in TRANSACTION_TYPES else default


def is_income(transaction_type):
    return normalize_transaction_type(transaction_type) in INCOME_TYPES


def is_expense(transaction_type):
    return normalize_transaction_type(transaction_type) in EXPENSE_TYPES


def is_receivable_event(transaction_type):
    return normalize_transaction_type(transaction_type) in RECEIVABLE_TYPES


def is_liability_event(transaction_type):
    return normalize_transaction_type(transaction_type) in LIABILITY_TYPES


def is_transfer(transaction_type):
    return normalize_transaction_type(transaction_type) in TRANSFER_TYPES


def profit_effect(transaction_type, amount):
    """Return the transaction's effect on profit/loss."""
    amount = Decimal(str(amount or 0))
    if is_income(transaction_type):
        return amount
    if is_expense(transaction_type):
        return -amount
    return Decimal("0")


def cash_effect(transaction_type, amount):
    """Return the transaction's effect on the selected cash account.

    This is intentionally separate from profit_effect: a loan received or a
    receivable recovered changes cash but is not operating income.
    """
    amount = Decimal(str(amount or 0))
    transaction_type = normalize_transaction_type(transaction_type)
    if transaction_type in {"income", "money_returned", "loan_received", "transfer_in"}:
        return amount
    if transaction_type in {"expense", "money_lent", "loan_repayment", "transfer_out"}:
        return -amount
    return Decimal("0")


def receivable_effect(transaction_type, amount):
    """Return the effect on money owed to the user."""
    amount = Decimal(str(amount or 0))
    transaction_type = normalize_transaction_type(transaction_type)
    if transaction_type == "money_lent":
        return amount
    if transaction_type == "money_returned":
        return -amount
    return Decimal("0")


def liability_effect(transaction_type, amount):
    """Return the effect on money the user owes to others."""
    amount = Decimal(str(amount or 0))
    transaction_type = normalize_transaction_type(transaction_type)
    if transaction_type == "loan_received":
        return amount
    if transaction_type == "loan_repayment":
        return -amount
    return Decimal("0")


def type_label(transaction_type):
    transaction_type = normalize_transaction_type(transaction_type)
    return TYPE_LABELS.get(transaction_type, "Expense")
