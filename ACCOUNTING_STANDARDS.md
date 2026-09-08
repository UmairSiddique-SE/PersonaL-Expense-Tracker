# Accounting Upgrade — Phase 1

This project is being upgraded from a simple income/expense tracker into a professional personal-finance accounting system.

## Core rule

A transaction's **cash movement** and its **profit/loss effect** are not always the same thing.

### Profit and loss
- Income increases profit.
- Expense decreases profit.
- Money given/lent does **not** create an expense.
- Money received back does **not** create income.
- Loan received does **not** create income.
- Loan repayment does **not** create an expense.
- Transfers between the user's own accounts do not create income or expense.

## Canonical transaction types

| Type | User-facing label | Profit/Loss | Cash movement | Balance effect |
|---|---|---|---|---|
| `income` | Income | Income + | In | — |
| `expense` | Expense | Expense - | Out | — |
| `money_lent` | Money Given | None | Out | Receivable + |
| `money_returned` | Money Received Back | None | In | Receivable - |
| `loan_received` | Loan Received | None | In | Liability + |
| `loan_repayment` | Loan Repayment | None | Out | Liability - |
| `transfer_in` | Transfer In | None | In | Account transfer |
| `transfer_out` | Transfer Out | None | Out | Account transfer |
| `adjustment` | Adjustment | Explicit | Explicit | Explicit |

## Example: Rs 5,000 lent and returned

The correct result is:

- Income: Rs 0
- Expense: Rs 0
- Money Given: Rs 5,000
- Money Received Back: Rs 5,000
- Outstanding Receivable: Rs 0
- Net cash effect: Rs 0

The Rs 5,000 recovery must never inflate total income.

## Existing-data compatibility

Existing records use `type=income` or `type=expense`. They remain valid and are treated as legacy records. No destructive migration is required for Phase 1.

New phases will add accounts, parties, receivables/payables, ledgers, reconciliation, financial statements, and audit history without changing the meaning of historical records.

## Planned statement rules

- **Profit & Loss:** income and expense only.
- **Statement of Financial Position:** assets, liabilities and equity.
- **Cash Flow:** actual cash movement, including lending/repayment and loans.
- **Receivables:** money lent less money recovered, by person/party.
- **Payables:** money owed to others less repayments, by person/party.
- **Trial Balance:** total debits must equal total credits once double-entry posting is enabled.

## Phase sequence

1. Accounting transaction model and backward compatibility.
2. Transaction-entry UX for income, expense, lending, recovery, loans and transfers.
3. Account/wallet and party ledgers.
4. Dashboard and summary with separate profit, cash, receivable and payable figures.
5. Professional financial statements and accountant-level PDF reporting.
6. Reconciliation, audit trail, period closing and integrity checks.
