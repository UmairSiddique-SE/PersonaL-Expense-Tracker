from decimal import Decimal

from accounting import (
    cash_effect,
    is_expense,
    is_income,
    liability_effect,
    normalize_transaction_type,
    profit_effect,
    receivable_effect,
)


def test_money_returned_is_not_income():
    assert not is_income("money_returned")
    assert profit_effect("money_returned", 5000) == Decimal("0")
    assert cash_effect("money_returned", 5000) == Decimal("5000")
    assert receivable_effect("money_returned", 5000) == Decimal("-5000")


def test_money_lent_is_not_expense():
    assert not is_expense("money_lent")
    assert profit_effect("money_lent", 5000) == Decimal("0")
    assert cash_effect("money_lent", 5000) == Decimal("-5000")
    assert receivable_effect("money_lent", 5000) == Decimal("5000")


def test_loan_received_is_not_income():
    assert not is_income("loan_received")
    assert profit_effect("loan_received", 20000) == Decimal("0")
    assert cash_effect("loan_received", 20000) == Decimal("20000")
    assert liability_effect("loan_received", 20000) == Decimal("20000")


def test_loan_repayment_is_not_expense():
    assert not is_expense("loan_repayment")
    assert profit_effect("loan_repayment", 5000) == Decimal("0")
    assert cash_effect("loan_repayment", 5000) == Decimal("-5000")
    assert liability_effect("loan_repayment", 5000) == Decimal("-5000")


def test_legacy_types_remain_supported():
    assert normalize_transaction_type("income") == "income"
    assert normalize_transaction_type("expense") == "expense"
    assert normalize_transaction_type("returned") == "money_returned"
    assert normalize_transaction_type("lent") == "money_lent"
