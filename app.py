import io
import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps

from bson.objectid import ObjectId
from flask import Flask, flash, redirect, render_template, request, send_file, send_from_directory, session, url_for
from pymongo import MongoClient
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")
app.permanent_session_lifetime = timedelta(days=30)
app.config.update(
    SEND_FILE_MAX_AGE_DEFAULT=31536000,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("MONGO_DB_NAME", "expense_db")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000, retryWrites=True)
db = client[DB_NAME]
expenses_collection = db["expenses"]
users_collection = db["users"]


def ensure_indexes():
    try:
        users_collection.create_index("username", unique=True, name="uq_username")
        expenses_collection.create_index([("user_id", 1), ("created_at", -1), ("_id", -1)], name="user_created_desc")
        expenses_collection.create_index([("user_id", 1), ("date", -1)], name="user_date_desc")
    except Exception as exc:
        app.logger.warning("Database indexes could not be created: %s", exc)

ensure_indexes()


def utc_now():
    return datetime.now(timezone.utc)


def parse_amount(value):
    try:
        amount = Decimal(str(value or "").strip().replace(",", ""))
        if not amount.is_finite() or amount <= 0:
            raise ValueError
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Amount must be a valid number greater than 0.")


def money(value):
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def parse_record_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError("Please enter a valid date.")


def normalize_text(value, max_length=500):
    return re.sub(r"\s+", " ", str(value or "").strip())[:max_length]


def normalize_category(value, default="Other"):
    value = normalize_text(value, 80)
    return value if value else default


def safe_object_id(value):
    try:
        return ObjectId(value)
    except Exception:
        return None


def record_created_at(record):
    value = record.get("created_at")
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    oid = record.get("_id")
    if isinstance(oid, ObjectId):
        return oid.generation_time
    return datetime.min.replace(tzinfo=timezone.utc)


def sort_by_added(records, newest_first=True):
    return sorted(records, key=record_created_at, reverse=newest_first)


def record_to_view(record):
    item = dict(record)
    item["amount"] = float(money(item.get("amount")))
    return item


def shift_months(year, month, offset):
    index = year * 12 + (month - 1) + offset
    return index // 12, index % 12 + 1


def last_six_months(today=None):
    today = today or date.today()
    result = []
    for offset in range(-5, 1):
        year, month = shift_months(today.year, today.month, offset)
        result.append((year, month, date(year, month, 1).strftime("%b %Y")))
    return result


def transaction_date(record):
    try:
        return parse_record_date(record.get("date"))
    except ValueError:
        return None


def login_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    if request.args.get("source") == "pwa":
        return redirect(url_for("dashboard" if session.get("user_id") else "login"))
    return render_template("index.html")


@app.route("/index")
def index_alias():
    return redirect(url_for("index"))


@app.route("/sw.js")
def service_worker():
    return send_from_directory(app.root_path, "sw.js")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = normalize_text(request.form.get("username"), 120).lower()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")
        try:
            user = users_collection.find_one({"username": username})
        except Exception:
            app.logger.exception("Login database error")
            flash("Database connection error. Please try again.", "danger")
            return render_template("login.html")
        if user and check_password_hash(user.get("password", ""), password):
            session.clear()
            session.permanent = bool(request.form.get("remember_me"))
            session["user_id"] = str(user["_id"])
            session["first_name"] = user.get("first_name", "User")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = normalize_text(request.form.get("first_name"), 80)
        username = normalize_text(request.form.get("username"), 120).lower()
        password = request.form.get("password", "")
        security_question = normalize_text(request.form.get("security_question"), 200)
        security_answer = normalize_text(request.form.get("security_answer"), 200).lower()
        if not first_name or not username or not password or not security_question or not security_answer:
            flash("All fields are required.", "danger")
            return redirect(url_for("signup"))
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
            return redirect(url_for("signup"))
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("signup"))
        try:
            if users_collection.find_one({"username": username}):
                flash("User already exists. Please login.", "danger")
                return redirect(url_for("signup"))
            users_collection.insert_one({
                "first_name": first_name,
                "username": username,
                "password": generate_password_hash(password),
                "security_question": security_question,
                "security_answer": generate_password_hash(security_answer),
                "custom_categories": [],
                "created_at": utc_now(),
            })
        except Exception:
            app.logger.exception("Signup database error")
            flash("Unable to create the account. Please try again.", "danger")
            return redirect(url_for("signup"))
        flash("Signup successful! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        step = request.form.get("step", "lookup")
        username = normalize_text(request.form.get("username"), 120).lower()
        if not username:
            flash("Please enter your registered username.", "danger")
            return render_template("forgot.html")
        try:
            user = users_collection.find_one({"username": username})
        except Exception:
            app.logger.exception("Password reset database error")
            flash("Database connection error.", "danger")
            return render_template("forgot.html")
        if not user:
            flash("Invalid username.", "danger")
            return render_template("forgot.html")
        question = user.get("security_question")
        if not question:
            flash("No recovery question is configured for this account.", "danger")
            return render_template("forgot.html")
        if step == "lookup":
            return render_template("forgot.html", step="question", username=username, question=question)
        security_answer = normalize_text(request.form.get("security_answer"), 200).lower()
        new_password = request.form.get("new_password", "")
        stored_answer = user.get("security_answer", "")
        try:
            valid_answer = check_password_hash(stored_answer, security_answer)
        except (ValueError, TypeError):
            valid_answer = security_answer == str(stored_answer).lower()
        if not valid_answer:
            flash("Security answer does not match.", "danger")
            return render_template("forgot.html", step="question", username=username, question=question)
        if len(new_password) < 8:
            flash("New password must be at least 8 characters.", "danger")
            return render_template("forgot.html", step="question", username=username, question=question)
        try:
            update = {"password": generate_password_hash(new_password)}
            if stored_answer == security_answer:
                update["security_answer"] = generate_password_hash(security_answer)
            users_collection.update_one({"_id": user["_id"]}, {"$set": update})
        except Exception:
            app.logger.exception("Password reset update error")
            flash("Unable to reset password. Please try again.", "danger")
            return render_template("forgot.html", step="question", username=username, question=question)
        flash("Password reset successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("forgot.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/settings")
@login_required
def settings():
    oid = safe_object_id(session.get("user_id"))
    if not oid:
        session.clear()
        return redirect(url_for("login"))
    try:
        user = users_collection.find_one({"_id": oid})
    except Exception:
        user = None
    if not user:
        session.clear()
        return redirect(url_for("login"))
    return render_template("settings.html", user=user)


@app.route("/update_name", methods=["POST"])
@login_required
def update_name():
    oid = safe_object_id(session.get("user_id"))
    first_name = normalize_text(request.form.get("first_name"), 80)
    if not oid or not first_name:
        flash("Name cannot be empty.", "danger")
        return redirect(url_for("settings"))
    try:
        users_collection.update_one({"_id": oid}, {"$set": {"first_name": first_name}})
        session["first_name"] = first_name
        flash("Name updated successfully.", "success")
    except Exception:
        app.logger.exception("Name update error")
        flash("Error updating name.", "danger")
    return redirect(url_for("settings"))


@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    oid = safe_object_id(session.get("user_id"))
    current_pw = request.form.get("current_password", "")
    new_pw = request.form.get("new_password", "")
    confirm_pw = request.form.get("confirm_password", "")
    try:
        user = users_collection.find_one({"_id": oid}) if oid else None
    except Exception:
        user = None
    if not user or not check_password_hash(user.get("password", ""), current_pw):
        flash("Incorrect current password.", "danger")
        return redirect(url_for("settings"))
    if len(new_pw) < 8:
        flash("New password must be at least 8 characters long.", "danger")
        return redirect(url_for("settings"))
    if new_pw != confirm_pw:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("settings"))
    users_collection.update_one({"_id": oid}, {"$set": {"password": generate_password_hash(new_pw)}})
    session.clear()
    flash("Password updated successfully. Please login again.", "success")
    return redirect(url_for("login"))


@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    oid = safe_object_id(session.get("user_id"))
    password = request.form.get("confirm_delete_password", "")
    try:
        user = users_collection.find_one({"_id": oid}) if oid else None
        if not user or not check_password_hash(user.get("password", ""), password):
            flash("Incorrect password. Account deletion cancelled.", "danger")
            return redirect(url_for("settings"))
        expenses_collection.delete_many({"user_id": str(oid)})
        users_collection.delete_one({"_id": oid})
    except Exception:
        app.logger.exception("Account deletion error")
        flash("Account could not be deleted. Please try again.", "danger")
        return redirect(url_for("settings"))
    session.clear()
    flash("Your account and associated records have been permanently deleted.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    uid = session.get("user_id")
    try:
        transactions = list(expenses_collection.find({"user_id": uid}))
    except Exception:
        app.logger.exception("Dashboard query error")
        transactions = []
    today = date.today()
    total_income = Decimal("0.00")
    total_expense = Decimal("0.00")
    month_income = Decimal("0.00")
    month_expense = Decimal("0.00")
    expense_category_totals = {}
    income_category_totals = {}
    six_months = last_six_months(today)
    month_keys = [f"{y:04d}-{m:02d}" for y, m, _ in six_months]
    month_labels = [label for _, _, label in six_months]
    chart_income_map = {key: Decimal("0.00") for key in month_keys}
    chart_expense_map = {key: Decimal("0.00") for key in month_keys}
    for item in transactions:
        amount = money(item.get("amount"))
        item_type = str(item.get("type", "expense")).lower()
        category = normalize_category(item.get("category"))
        trans_date = transaction_date(item)
        if item_type == "income":
            total_income += amount
            income_category_totals[category] = income_category_totals.get(category, Decimal("0.00")) + amount
        else:
            total_expense += amount
            expense_category_totals[category] = expense_category_totals.get(category, Decimal("0.00")) + amount
        if trans_date:
            month_key = trans_date.strftime("%Y-%m")
            if trans_date.year == today.year and trans_date.month == today.month:
                if item_type == "income":
                    month_income += amount
                else:
                    month_expense += amount
            if month_key in chart_income_map:
                if item_type == "income":
                    chart_income_map[month_key] += amount
                else:
                    chart_expense_map[month_key] += amount
    total_savings = total_income - total_expense
    month_savings = month_income - month_expense
    saving_pct = round(total_savings / total_income * Decimal("100"), 1) if total_income > 0 else Decimal("0.0")
    expense_pct = round(total_expense / total_income * Decimal("100"), 1) if total_income > 0 else Decimal("0.0")
    top_expense_category = max(expense_category_totals, key=expense_category_totals.get) if expense_category_totals else "None"
    top_income_source = max(income_category_totals, key=income_category_totals.get) if income_category_totals else "None"
    return render_template(
        "dashboard.html",
        total_income=float(total_income), total_expense=float(total_expense), total_savings=float(total_savings),
        total_saving=float(total_savings), total_balance=float(total_savings), month_income=float(month_income),
        month_expense=float(month_expense), month_savings=float(month_savings), month_saving=float(month_savings),
        month_balance=float(month_savings), total_records=len(transactions), top_category=top_expense_category,
        top_expense_category=top_expense_category, top_income_source=top_income_source, saving_pct=float(saving_pct),
        expense_pct=float(expense_pct), chart_labels=month_labels,
        chart_income_data=[float(chart_income_map[k]) for k in month_keys],
        chart_expense_data=[float(chart_expense_map[k]) for k in month_keys],
    )


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    uid = session.get("user_id")
    if request.method == "POST":
        record_type = str(request.form.get("record_type", "expense")).lower()
        if record_type not in {"income", "expense"}:
            record_type = "expense"
        try:
            amount = parse_amount(request.form.get("amount"))
            record_date = parse_record_date(request.form.get("date"))
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("add") + f"?tab={record_type}")
        description = normalize_text(request.form.get("description"), 500)
        category = normalize_category(request.form.get("category"), "Salary" if record_type == "income" else "Other")
        if record_type == "expense" and request.form.get("category") == "custom":
            category = normalize_category(request.form.get("custom_category"), "Other")
            try:
                users_collection.update_one({"_id": ObjectId(uid)}, {"$addToSet": {"custom_categories": category}})
            except Exception:
                app.logger.warning("Could not save custom category", exc_info=True)
        try:
            now = utc_now()
            expenses_collection.insert_one({
                "user_id": uid,
                "type": record_type,
                # Stored as a normalized 2-decimal BSON double; calculations are performed with Decimal.
                "amount": float(amount),
                "category": category,
                "date": record_date.isoformat(),
                "description": description,
                "created_at": now,
                "updated_at": now,
            })
            flash(f"{record_type.capitalize()} added successfully!", "success")
        except Exception:
            app.logger.exception("Record insert error")
            flash("Database error saving record.", "danger")
        return redirect(url_for("add") + f"?tab={record_type}")
    try:
        user_data = users_collection.find_one({"_id": ObjectId(uid)})
    except Exception:
        user_data = None
    custom_categories = user_data.get("custom_categories", []) if user_data else []
    try:
        latest = expenses_collection.find_one({"user_id": uid, "type": "expense"}, sort=[("created_at", -1), ("_id", -1)])
    except Exception:
        latest = None
    if not latest:
        try:
            latest = expenses_collection.find_one({"user_id": uid, "type": "expense"}, sort=[("_id", -1)])
        except Exception:
            latest = None
    return render_template(
        "add.html", custom_categories=custom_categories, today_date=date.today().isoformat(),
        last_used_category=latest.get("category", "") if latest else "", active_tab=request.args.get("tab", "expense")
    )


@app.route("/view")
@login_required
def view():
    uid = session.get("user_id")
    filter_type = request.args.get("type", "all").lower()
    query = {"user_id": uid}
    if filter_type in {"expense", "income"}:
        query["type"] = filter_type
    else:
        filter_type = "all"
    try:
        expenses = list(expenses_collection.find(query).sort([("created_at", -1), ("_id", -1)]))
        expenses = [record_to_view(item) for item in sort_by_added(expenses, newest_first=True)]
    except Exception:
        app.logger.exception("View records query error")
        expenses = []
    return render_template("view.html", expenses=expenses, filter_type=filter_type)


@app.route("/delete_custom_category", methods=["POST", "GET"])
@login_required
def delete_custom_category():
    uid = session.get("user_id")
    cat_name = normalize_text(request.form.get("name") or request.args.get("name"), 80)
    if cat_name:
        try:
            users_collection.update_one({"_id": ObjectId(uid)}, {"$pull": {"custom_categories": cat_name}})
            flash(f"Category '{cat_name}' deleted successfully!", "success")
        except Exception:
            app.logger.exception("Custom category deletion error")
            flash("Error deleting category.", "danger")
    return redirect(url_for("add"))


@app.route("/delete/<id>", methods=["POST", "GET"])
@login_required
def delete(id):
    oid = safe_object_id(id)
    if not oid:
        flash("Invalid record ID.", "danger")
        return redirect(url_for("view"))
    try:
        result = expenses_collection.delete_one({"_id": oid, "user_id": session.get("user_id")})
        flash("Record deleted successfully!" if result.deleted_count else "Record not found or access denied.", "success" if result.deleted_count else "danger")
    except Exception:
        app.logger.exception("Record deletion error")
        flash("Error deleting record.", "danger")
    return redirect(url_for("view"))


@app.route("/edit/<id>", methods=["GET", "POST"])
@login_required
def edit(id):
    uid = session.get("user_id")
    oid = safe_object_id(id)
    if not oid:
        flash("Invalid record ID.", "danger")
        return redirect(url_for("view"))
    try:
        expense = expenses_collection.find_one({"_id": oid, "user_id": uid})
    except Exception:
        expense = None
    if not expense:
        flash("Record not found or access denied.", "danger")
        return redirect(url_for("view"))
    if request.method == "POST":
        trans_type = str(request.form.get("type", expense.get("type", "expense"))).lower()
        if trans_type not in {"expense", "income"}:
            flash("Invalid transaction type.", "danger")
            return redirect(url_for("edit", id=id))
        try:
            amount = parse_amount(request.form.get("amount"))
            record_date = parse_record_date(request.form.get("date"))
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("edit", id=id))
        category = normalize_category(request.form.get("category"), "Salary" if trans_type == "income" else "Other")
        description = normalize_text(request.form.get("description"), 500)
        try:
            expenses_collection.update_one(
                {"_id": oid, "user_id": uid},
                {"$set": {"type": trans_type, "amount": float(amount), "category": category,
                          "date": record_date.isoformat(), "description": description, "updated_at": utc_now()}}
            )
            flash("Record updated successfully!", "success")
        except Exception:
            app.logger.exception("Record update error")
            flash("Error updating record.", "danger")
        return redirect(url_for("view"))
    return render_template("edit.html", expense=record_to_view(expense))


# -----------------------------
# Summary / reports
# -----------------------------
def summary_period_matches(trans_date, view_type, selected_date, from_date, to_date, today):
    if not trans_date:
        return False
    if view_type == "overall":
        return True
    if view_type == "weekly":
        return today - timedelta(days=6) <= trans_date <= today
    if view_type == "monthly":
        return trans_date.year == today.year and trans_date.month == today.month
    if view_type == "daily":
        return trans_date.isoformat() == selected_date
    if view_type == "range" and from_date and to_date:
        return from_date <= trans_date.isoformat() <= to_date
    return False


@app.route("/summary")
@login_required
def summary():
    uid = session.get("user_id")
    view_type = request.args.get("type", "overall").lower()
    if view_type not in {"overall", "weekly", "monthly", "daily", "range"}:
        view_type = "overall"
    selected_date = request.args.get("date", date.today().isoformat())
    selected_category = normalize_text(request.args.get("category"), 80)
    active_tab = request.args.get("tab", "expense").lower()
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")
    try:
        transactions = list(expenses_collection.find({"user_id": uid}))
    except Exception:
        app.logger.exception("Summary query error")
        transactions = []
    today = date.today()
    timeframes = ["overall", "weekly", "monthly", "daily"]
    expense_data = {tf: {} for tf in timeframes}
    income_data = {tf: {} for tf in timeframes}
    income_totals = {tf: Decimal("0.00") for tf in timeframes}
    expense_totals = {tf: Decimal("0.00") for tf in timeframes}
    savings_totals = {tf: Decimal("0.00") for tf in timeframes}
    category_items = []
    category_filter = bool(selected_category and selected_category.lower() != "all")
    for trans in transactions:
        amount = money(trans.get("amount"))
        category = normalize_category(trans.get("category"))
        trans_type = str(trans.get("type", "expense")).lower()
        trans_date = transaction_date(trans)
        if not trans_date:
            continue
        matches = {
            "overall": True,
            "weekly": today - timedelta(days=6) <= trans_date <= today,
            "monthly": trans_date.year == today.year and trans_date.month == today.month,
            "daily": trans_date.isoformat() == selected_date,
        }
        for tf, matched in matches.items():
            if matched:
                if trans_type == "income":
                    income_totals[tf] += amount
                    income_data[tf][category] = income_data[tf].get(category, Decimal("0.00")) + amount
                else:
                    expense_totals[tf] += amount
                    expense_data[tf][category] = expense_data[tf].get(category, Decimal("0.00")) + amount
        if category_filter and category.lower() == selected_category.lower() and summary_period_matches(trans_date, view_type, selected_date, from_date, to_date, today):
            category_items.append(trans)
    for tf in timeframes:
        savings_totals[tf] = income_totals[tf] - expense_totals[tf]
    total_income = income_totals["overall"]
    total_expense = expense_totals["overall"]
    total_saving = savings_totals["overall"]
    saving_pct = total_saving / total_income * Decimal("100") if total_income > 0 else Decimal("0")
    expense_pct = total_expense / total_income * Decimal("100") if total_income > 0 else Decimal("0")
    category_items = [record_to_view(x) for x in sort_by_added(category_items, newest_first=True)]
    return render_template(
        "summary.html",
        expense_data={tf: {k: float(v) for k, v in data.items()} for tf, data in expense_data.items()},
        income_data={tf: {k: float(v) for k, v in data.items()} for tf, data in income_data.items()},
        totals={"income": {tf: float(v) for tf, v in income_totals.items()}, "expense": {tf: float(v) for tf, v in expense_totals.items()}, "savings": {tf: float(v) for tf, v in savings_totals.items()}},
        income_totals={tf: float(v) for tf, v in income_totals.items()}, expense_totals={tf: float(v) for tf, v in expense_totals.items()},
        total_income=float(total_income), total_expense=float(total_expense), total_saving=float(total_saving),
        saving_pct=float(round(saving_pct, 1)), expense_pct=float(round(expense_pct, 1)), selected_date=selected_date,
        view_type=view_type, active_tab=active_tab, selected_category=selected_category, category_items=category_items,
        is_category_filtered=category_filter, from_date=from_date, to_date=to_date,
    )


@app.route("/summary/details")
@login_required
def summary_details():
    uid = session.get("user_id")
    category = normalize_text(request.args.get("category"), 80)
    view_type = request.args.get("type", "overall").lower()
    selected_date = request.args.get("date", date.today().isoformat())
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")
    try:
        transactions = list(expenses_collection.find({"user_id": uid}))
    except Exception:
        transactions = []
    today = date.today()
    filtered = []
    total = Decimal("0.00")
    for trans in transactions:
        if category and normalize_category(trans.get("category")).lower() != category.lower():
            continue
        trans_date = transaction_date(trans)
        if not summary_period_matches(trans_date, view_type, selected_date, from_date, to_date, today):
            continue
        total += money(trans.get("amount"))
        filtered.append(trans)
    filtered = [record_to_view(x) for x in sort_by_added(filtered, newest_first=True)]
    filter_text = {"weekly": "Last 7 days", "monthly": "Current month", "daily": f"Date: {selected_date}", "range": f"{from_date} to {to_date}"}.get(view_type, "Overall category breakdown")
    return render_template("summary_details.html", category=category, expenses=filtered, total=float(total), filter_text=filter_text, view_type=view_type, selected_date=selected_date, from_date=from_date, to_date=to_date)


@app.route("/summary/report")
@login_required
def download_report():
    uid = session.get("user_id")
    view_type = request.args.get("type", "overall").lower()
    if view_type not in {"overall", "weekly", "monthly", "daily", "range"}:
        view_type = "overall"
    selected_date = request.args.get("date", date.today().isoformat())
    selected_category = normalize_text(request.args.get("category"), 80)
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")
    try:
        items = list(expenses_collection.find({"user_id": uid}))
    except Exception:
        items = []
    today = date.today()
    filtered = []
    total_income = Decimal("0.00")
    total_expense = Decimal("0.00")
    for item in items:
        trans_date = transaction_date(item)
        category = normalize_category(item.get("category"))
        if not summary_period_matches(trans_date, view_type, selected_date, from_date, to_date, today):
            continue
        if selected_category and selected_category.lower() != "all" and category.lower() != selected_category.lower():
            continue
        filtered.append(item)
        amount = money(item.get("amount"))
        if str(item.get("type", "expense")).lower() == "income":
            total_income += amount
        else:
            total_expense += amount
    filtered = sort_by_added(filtered, newest_first=False)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm, leftMargin=15 * mm, rightMargin=15 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], textColor=colors.HexColor("#0284c7"), fontSize=18, spaceAfter=6)
    subtitle_style = ParagraphStyle("SubtitleStyle", parent=styles["Normal"], textColor=colors.HexColor("#475569"), fontSize=9, spaceAfter=10)
    elements = [Paragraph("Financial Tracker – Income & Expense Statement", title_style)]
    period = view_type.capitalize()
    if view_type == "daily": period += f" ({selected_date})"
    elif view_type == "monthly": period += " (Current Month)"
    elif view_type == "weekly": period += " (Last 7 Days)"
    elif view_type == "range": period += f" ({from_date} to {to_date})"
    elements.append(Paragraph(f"<b>User:</b> {session.get('first_name', 'User')} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Report Period:</b> {period} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Generated:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}", subtitle_style))
    net = total_income - total_expense
    net_color = "#059669" if net >= 0 else "#e11d48"
    elements.append(Paragraph(f"<b>Total Income:</b> <font color='#059669'>Rs {total_income:,.2f}</font> &nbsp;&nbsp;&nbsp; <b>Total Expense:</b> <font color='#e11d48'>Rs {total_expense:,.2f}</font> &nbsp;&nbsp;&nbsp; <b>Net Savings:</b> <font color='{net_color}'>Rs {net:,.2f}</font>", ParagraphStyle("SummaryP", parent=styles["Normal"], fontSize=10, spaceAfter=12)))
    table_data = [["#", "Date", "Type", "Category", "Description", "Amount (Rs)"]]
    for i, item in enumerate(filtered, 1):
        table_data.append([str(i), item.get("date", "-"), str(item.get("type", "expense")).capitalize(), normalize_category(item.get("category"), "-"), normalize_text(item.get("description"), 100) or "-", f"{money(item.get('amount')):,.2f}"])
    if not filtered:
        elements.append(Paragraph("No financial records found for this selection.", styles["Normal"]))
    else:
        table = Table(table_data, colWidths=[20, 60, 55, 80, 185, 85], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")), ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"), ("ALIGN", (5, 0), (5, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]), ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"statement_{view_type}_{datetime.now().strftime('%Y%m%d')}.pdf")


@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(app.root_path, "sitemap.xml")


@app.errorhandler(404)
def page_not_found(_error):
    return redirect(url_for("dashboard" if session.get("user_id") else "index"))


@app.errorhandler(500)
def internal_server_error(_error):
    flash("An internal server error occurred. Please try again.", "danger")
    return redirect(url_for("dashboard" if session.get("user_id") else "index"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
