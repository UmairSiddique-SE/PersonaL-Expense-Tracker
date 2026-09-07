# Personal Expense Tracker

A production-focused personal finance tracker built with Flask, MongoDB, server-rendered HTML/CSS/JavaScript, and PDF reporting.

## Core features

- Income and expense records
- Explicit record creation order: newly added records stay newest-first regardless of transaction date
- Edit and delete with per-user ownership checks
- Accurate money calculations using Python `Decimal`
- Overall, weekly, monthly, daily and custom-range analytics
- Income/expense category breakdowns
- Six-calendar-month dashboard trend chart
- PDF financial statements
- Secure password hashing and recovery-answer hashing
- Account settings, password change and account deletion
- MongoDB indexes for user and record queries
- Production-safe secret configuration
- PWA/service-worker support

## Stack

- Backend: Flask
- Database: MongoDB / MongoDB Atlas
- Security: Werkzeug password hashing + secure Flask sessions
- Reports: ReportLab
- Hosting configuration: Vercel Python runtime

## Environment variables

Create a local `.env` or configure these variables in the deployment platform:

```text
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=expense_db
SECRET_KEY=replace-with-a-long-random-secret
COOKIE_SECURE=0
FLASK_DEBUG=0
```

For HTTPS production deployments, set `COOKIE_SECURE=1`.

## Local run

```bash
pip install -r requirements.txt
python app.py
```

The application expects MongoDB to be available at `MONGO_URI`. The old JSON/mongomock fallback has intentionally been removed so development and production cannot silently use different databases.

## Important data behavior

Each new transaction receives a `created_at` timestamp. The records screen and generated statements use that timestamp for insertion order, with MongoDB `ObjectId` creation time as a legacy fallback. The transaction `date` remains the date of the financial event and does not control insertion order.

Money input is validated as positive and normalized to two decimal places before storage; calculations convert stored values to `Decimal` to avoid common floating-point calculation surprises.
