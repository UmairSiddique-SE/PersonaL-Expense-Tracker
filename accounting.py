"""Core accounting rules for PersonaL Expense Tracker.

Phase 1 deliberately keeps the existing MongoDB records compatible while giving
later phases one canonical vocabulary for transaction classification.
"""

from decimal import Decimal

TRANSACTION_TYPES = (
    "income", "expense", "money_lent", "money_returned", "loan_received",
    "loan_repayment", "transfer_in", "transfer_out", "adjustment",
)

TYPE_LABELS = {
    "income": "Income", "expense": "Expense", "money_lent": "Money Given",
    "money_returned": "Money Received Back", "loan_received": "Loan Received",
    "loan_repayment": "Loan Repayment", "transfer_in": "Transfer In",
    "transfer_out": "Transfer Out", "adjustment": "Adjustment",
}

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
        "lent": "money_lent", "loan_given": "money_lent", "money_given": "money_lent",
        "returned": "money_returned", "loan_returned": "money_returned",
        "loan_in": "loan_received", "borrowed": "loan_received",
        "loan_out": "loan_repayment", "repaid": "loan_repayment",
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
    amount = Decimal(str(amount or 0))
    if is_income(transaction_type):
        return amount
    if is_expense(transaction_type):
        return -amount
    return Decimal("0")


def cash_effect(transaction_type, amount):
    amount = Decimal(str(amount or 0))
    transaction_type = normalize_transaction_type(transaction_type)
    if transaction_type in {"income", "money_returned", "loan_received", "transfer_in"}:
        return amount
    if transaction_type in {"expense", "money_lent", "loan_repayment", "transfer_out"}:
        return -amount
    return Decimal("0")


def receivable_effect(transaction_type, amount):
    amount = Decimal(str(amount or 0))
    transaction_type = normalize_transaction_type(transaction_type)
    if transaction_type == "money_lent":
        return amount
    if transaction_type == "money_returned":
        return -amount
    return Decimal("0")


def liability_effect(transaction_type, amount):
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


# The PDF route already contains the report data/calculations. This hook only
# enhances its ReportLab tables, so it cannot change the web UI or accounting.
def _install_pdf_table_theme():
    try:
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import Table, TableStyle
        if getattr(Table, "_expense_tracker_theme", False):
            return
        original_set_style = Table.setStyle
        green = HexColor("#059669")
        red = HexColor("#E11D48")
        blue = HexColor("#2563EB")
        green_bg = HexColor("#ECFDF5")
        red_bg = HexColor("#FFF1F2")
        blue_bg = HexColor("#EFF6FF")
        stripe = HexColor("#F8FAFC")

        def themed_set_style(self, tblstyle):
            commands = list(tblstyle.getCommands())
            cells = getattr(self, "_cellvalues", [])
            rows = len(cells)
            cols = len(cells[0]) if rows else 0
            extra = []

            if rows == 3 and cols == 2:
                extra += [
                    ("BACKGROUND", (0, 0), (-1, 0), green_bg),
                    ("BACKGROUND", (0, 1), (-1, 1), red_bg),
                    ("BACKGROUND", (0, 2), (-1, 2), blue_bg),
                    ("TEXTCOLOR", (1, 0), (1, 0), green),
                    ("TEXTCOLOR", (1, 1), (1, 1), red),
                    ("TEXTCOLOR", (1, 2), (1, 2), blue),
                ]
            elif rows >= 2 and cols == 7:
                for row in range(1, rows):
                    if row % 2 == 0:
                        extra.append(("BACKGROUND", (0, row), (-1, row), stripe))
                extra += [
                    ("TEXTCOLOR", (4, 1), (4, -1), green),
                    ("TEXTCOLOR", (5, 1), (5, -1), red),
                    ("TEXTCOLOR", (6, 1), (6, -1), blue),
                ]
            elif rows == 2 and cols == 3:
                extra += [
                    ("BACKGROUND", (0, 0), (0, 1), green_bg),
                    ("BACKGROUND", (1, 0), (1, 1), red_bg),
                    ("BACKGROUND", (2, 0), (2, 1), blue_bg),
                    ("TEXTCOLOR", (0, 0), (0, -1), green),
                    ("TEXTCOLOR", (1, 0), (1, -1), red),
                    ("TEXTCOLOR", (2, 0), (2, -1), blue),
                ]

            if extra:
                original_set_style(self, TableStyle(commands + extra))
            else:
                original_set_style(self, tblstyle)

        Table.setStyle = themed_set_style
        Table._expense_tracker_theme = True
    except Exception:
        # PDF styling must never prevent the application from starting.
        pass


_install_pdf_table_theme()
