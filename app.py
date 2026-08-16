import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta

from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io
from datetime import datetime
app = Flask(__name__)
app.secret_key = "expense_secret_key"
app.permanent_session_lifetime = timedelta(days=30)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000

# MongoDB Connection with automatic local fallback
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
is_mock_db = False
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1200, connectTimeoutMS=1200)
    client.admin.command('ping')
    print("Connected to MongoDB successfully!")
except Exception:
    print("MongoDB server not reachable locally. Initializing local database engine...")
    try:
        import mongomock
        client = mongomock.MongoClient()
        is_mock_db = True
    except Exception:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1200, connectTimeoutMS=1200)

db = client['expense_db']
expenses_collection = db['expenses']
users_collection = db['users']

USERS_FILE = os.path.join(app.root_path, "users.json")
EXPENSES_FILE = os.path.join(app.root_path, "expenses.json")

def sync_local_db():
    if not is_mock_db:
        return
    try:
        import json
        users = list(users_collection.find())
        user_list = []
        for u in users:
            item = dict(u)
            item['_id'] = str(item['_id'])
            user_list.append(item)
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_list, f, indent=2)

        expenses = list(expenses_collection.find())
        exp_list = []
        for e in expenses:
            item = dict(e)
            item['_id'] = str(item['_id'])
            exp_list.append(item)
        with open(EXPENSES_FILE, 'w', encoding='utf-8') as f:
            json.dump(exp_list, f, indent=2)
    except Exception as e:
        print(f"Local storage sync note: {e}")

# Load initial data if using mock DB
if is_mock_db:
    import json
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    if '_id' in item:
                        item['_id'] = ObjectId(item['_id'])
                    users_collection.insert_one(item)
        except Exception:
            pass
    if os.path.exists(EXPENSES_FILE):
        try:
            with open(EXPENSES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    if '_id' in item:
                        item['_id'] = ObjectId(item['_id'])
                    expenses_collection.insert_one(item)
        except Exception:
            pass

@app.after_request
def after_request_handler(response):
    if request.method in ["POST", "PUT", "DELETE"]:
        sync_local_db()
    return response

# Create database indexes for maximum speed & query performance
try:
    users_collection.create_index([("username", 1)], unique=True)
    expenses_collection.create_index([("user_id", 1)])
    expenses_collection.create_index([("user_id", 1), ("date", -1)])
except Exception as e:
    print(f"MongoDB index setup note: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- AUTH ROUTES ---
@app.route("/")
def index():
    # Installed PWA app icon se khulne par (manifest start_url ke through) seedha login/dashboard
    if request.args.get('source') == 'pwa':
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    # Normal browser se aane par landing page dikhao
    return render_template('index.html')

@app.route("/index")
def index_alias():
    return redirect(url_for('index'))

@app.route('/sw.js')
def service_worker():
    return send_from_directory(app.root_path, 'sw.js')

@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session: 
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        raw_username = request.form.get("username")
        username = raw_username.lower() if raw_username else ""
        password = request.form.get("password")
        remember = request.form.get("remember_me")
        
        try:
            user = users_collection.find_one({"username": username})
        except Exception:
            flash("Database connection error. Please ensure MongoDB is running.", "danger")
            return render_template("login.html")
        
        if user and check_password_hash(user['password'], password):
            if remember:
                session.permanent = True
            else:
                session.permanent = False
            session['user_id'] = str(user['_id'])
            session['first_name'] = user.get('first_name', 'User')
            
            return redirect(url_for("dashboard"))
        
        flash("Invalid Username or Password!", "danger")
    return render_template("login.html")

@app.route("/biometric_login", methods=["POST"])
def biometric_login():
    data = request.get_json() or {}
    username = data.get("username", "").lower().strip()
    if not username:
        return {"status": "error", "message": "Username required"}, 400
    try:
        user = users_collection.find_one({"username": username})
    except Exception:
        return {"status": "error", "message": "Database connection error"}, 500
    if user:
        session.permanent = True
        session['user_id'] = str(user['_id'])
        session['first_name'] = user.get('first_name', 'User')
        return {"status": "success", "redirect": url_for("dashboard")}
    return {"status": "error", "message": "User not found"}, 404

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        
        raw_username = request.form.get("username")
        username = raw_username.lower().strip() if raw_username else ""
        password = request.form.get("password")
        security_question = request.form.get("security_question", "").strip()
        security_answer = request.form.get("security_answer", "").strip()
        
        if not username or not password or not security_question or not security_answer:
            flash("All fields are required!", "danger")
            return redirect(url_for("signup"))
        
        try:
            if users_collection.find_one({"username": username}):
                flash("User already exists! Please login.", "danger")
                return redirect(url_for("signup"))
            
            hashed_pw = generate_password_hash(password)
            users_collection.insert_one({
                "first_name": first_name,
                "username": username,
                "password": hashed_pw,
                "security_question": security_question,
                "security_answer": security_answer.lower()
            })
        except Exception:
            flash("Database error during registration. Please try again.", "danger")
            return redirect(url_for("signup"))
        
        flash("Signup successful! Please login.", "success")
        return redirect(url_for("login"))
        
    return render_template("signup.html")

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        step = request.form.get("step", "lookup")
        raw_username = request.form.get("username")
        username = raw_username.lower().strip() if raw_username else ""

        if not username:
            flash("Please enter your registered username.", "danger")
            return render_template("forgot.html")

        try:
            user = users_collection.find_one({"username": username})
        except Exception:
            flash("Database connection error.", "danger")
            return render_template("forgot.html")

        if not user:
            flash("Invalid username.", "danger")
            return render_template("forgot.html")

        if step == "lookup":
            question = user.get("security_question")
            if not question:
                flash("No security question set for this account. Contact support.", "danger")
                return render_template("forgot.html")
            return render_template("forgot.html", step="question", username=username, question=question)

        security_answer = request.form.get("security_answer", "").strip().lower()
        new_password = request.form.get("new_password", "")

        if not security_answer or not new_password:
            flash("Please answer the security question and provide a new password.", "danger")
            return render_template("forgot.html", step="question", username=username, question=user.get("security_question"))

        if security_answer != user.get("security_answer", ""):
            flash("Security answer does not match.", "danger")
            return render_template("forgot.html", step="question", username=username, question=user.get("security_question"))

        if len(new_password) < 8:
            flash("New password must be at least 8 characters.", "danger")
            return render_template("forgot.html", step="question", username=username, question=user.get("security_question"))

        users_collection.update_one({"_id": user["_id"]}, {"$set": {"password": generate_password_hash(new_password)}})
        flash("Password reset successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("forgot.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# --- SETTINGS & ACCOUNT MANAGEMENT ---
@app.route("/settings")
@login_required
def settings():
    uid = session.get('user_id')
    try:
        user = users_collection.find_one({"_id": ObjectId(uid)})
    except Exception:
        user = None
    if not user:
        session.clear()
        return redirect(url_for('login'))
    return render_template("settings.html", user=user)

@app.route("/update_name", methods=["POST"])
@login_required
def update_name():
    uid = session.get('user_id')
    first_name = request.form.get("first_name", "").strip()
    if not first_name:
        flash("Name cannot be empty!", "danger")
        return redirect(url_for("settings"))
    
    try:
        users_collection.update_one({"_id": ObjectId(uid)}, {"$set": {"first_name": first_name}})
        session['first_name'] = first_name
        flash("Name updated successfully!", "success")
    except Exception:
        flash("Error updating name.", "danger")
    return redirect(url_for("settings"))

@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    uid = session.get('user_id')
    current_pw = request.form.get("current_password", "")
    new_pw = request.form.get("new_password", "")
    confirm_pw = request.form.get("confirm_password", "")

    try:
        user = users_collection.find_one({"_id": ObjectId(uid)})
    except Exception:
        user = None

    if not user or not check_password_hash(user['password'], current_pw):
        flash("Incorrect current password!", "danger")
        return redirect(url_for("settings"))

    if len(new_pw) < 8:
        flash("New password must be at least 8 characters long!", "danger")
        return redirect(url_for("settings"))

    if new_pw != confirm_pw:
        flash("New passwords do not match!", "danger")
        return redirect(url_for("settings"))

    users_collection.update_one({"_id": ObjectId(uid)}, {"$set": {"password": generate_password_hash(new_pw)}})
    flash("Password updated successfully!", "success")
    return redirect(url_for("settings"))

@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    uid = session.get('user_id')
    password = request.form.get("confirm_delete_password", "")

    try:
        user = users_collection.find_one({"_id": ObjectId(uid)})
    except Exception:
        user = None

    if not user or not check_password_hash(user['password'], password):
        flash("Incorrect password! Account deletion cancelled.", "danger")
        return redirect(url_for("settings"))

    # Permanently delete user expenses and user profile from database
    try:
        expenses_collection.delete_many({"user_id": uid})
        users_collection.delete_one({"_id": ObjectId(uid)})
    except Exception:
        pass

    session.clear()
    flash("Your account and all associated expenses have been permanently deleted.", "success")
    return redirect(url_for("login"))

# --- DASHBOARD & EXPENSE/INCOME ROUTES ---
@app.route("/dashboard")
@login_required
def dashboard():
    uid = session.get('user_id')
    try:
        transactions = list(expenses_collection.find({"user_id": uid}))
    except Exception:
        transactions = []

    now = datetime.now()
    total_income = 0.0
    total_expense = 0.0
    month_income = 0.0
    month_expense = 0.0
    expense_category_totals = {}
    income_category_totals = {}

    # Build monthly tracking for the last 6 months for the chart
    month_keys = []
    month_labels = []
    for i in range(5, -1, -1):
        # Calculate date for roughly i months ago
        # Approx 30 days per month
        d = now - timedelta(days=i * 30)
        m_key = d.strftime('%Y-%m')
        if m_key not in month_keys:
            month_keys.append(m_key)
            month_labels.append(d.strftime('%b %Y'))

    chart_income_map = {k: 0.0 for k in month_keys}
    chart_expense_map = {k: 0.0 for k in month_keys}

    for item in transactions:
        amt = float(item.get('amount', 0))
        item_type = item.get('type', 'expense').lower()
        cat = item.get('category', 'Other')
        exp_date_str = item.get('date', '')

        if item_type == 'income':
            total_income += amt
            income_category_totals[cat] = income_category_totals.get(cat, 0.0) + amt
        else:
            total_expense += amt
            expense_category_totals[cat] = expense_category_totals.get(cat, 0.0) + amt

        try:
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
            if exp_date.month == now.month and exp_date.year == now.year:
                if item_type == 'income':
                    month_income += amt
                else:
                    month_expense += amt

            exp_m_key = exp_date.strftime('%Y-%m')
            if exp_m_key in chart_income_map:
                if item_type == 'income':
                    chart_income_map[exp_m_key] += amt
                else:
                    chart_expense_map[exp_m_key] += amt
        except (TypeError, ValueError):
            continue

    total_savings = total_income - total_expense
    month_savings = month_income - month_expense
    saving_pct = round((total_savings / total_income * 100), 1) if total_income > 0 else 0.0
    expense_pct = round((total_expense / total_income * 100), 1) if total_income > 0 else 0.0
    top_expense_category = max(expense_category_totals, key=expense_category_totals.get) if expense_category_totals else "None"
    top_income_source = max(income_category_totals, key=income_category_totals.get) if income_category_totals else "None"

    chart_labels = month_labels
    chart_income_data = [chart_income_map[k] for k in month_keys]
    chart_expense_data = [chart_expense_map[k] for k in month_keys]

    return render_template(
        "dashboard.html",
        total_income=total_income,
        total_expense=total_expense,
        total_savings=total_savings,
        total_saving=total_savings,
        total_balance=total_savings,
        month_income=month_income,
        month_expense=month_expense,
        month_savings=month_savings,
        month_saving=month_savings,
        month_balance=month_savings,
        total_records=len(transactions),
        top_category=top_expense_category,
        top_expense_category=top_expense_category,
        top_income_source=top_income_source,
        saving_pct=saving_pct,
        expense_pct=expense_pct,
        chart_labels=chart_labels,
        chart_income_data=chart_income_data,
        chart_expense_data=chart_expense_data
    )
    
@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    uid = session.get('user_id')

    if request.method == "POST":
        record_type = request.form.get("record_type", "expense")  # 'income' or 'expense'
        amount = request.form.get("amount")
        date = request.form.get("date")
        description = request.form.get("description", "")
        
        try:
            if record_type == "income":
                income_cat = request.form.get("category", "Salary").strip()
                if not income_cat:
                    income_cat = "Salary"
                expenses_collection.insert_one({
                    "user_id": uid,
                    "type": "income",
                    "amount": float(amount) if amount else 0.0,
                    "category": income_cat,
                    "date": date,
                    "description": description
                })
                flash("Income added successfully!", "success")
                return redirect(url_for("add") + "?tab=income")
            else:
                category = request.form.get("category")
                if category == 'custom':
                    custom_cat = request.form.get("custom_category", "").strip().capitalize()
                    if custom_cat:
                        category = custom_cat
                        users_collection.update_one(
                            {"_id": ObjectId(uid)},
                            {"$addToSet": {"custom_categories": category}}
                        )
                    else:
                        category = "Other"
                
                expenses_collection.insert_one({
                    "user_id": uid,
                    "type": "expense",
                    "amount": float(amount) if amount else 0.0,
                    "category": category,
                    "date": date,
                    "description": description
                })
                flash("Expense added successfully!", "success")
        except Exception:
            flash("Database error saving record.", "danger")
        
        return redirect(url_for("add") + "?tab=expense")

    
    # GET request - show form with previous categories
    try:
        user_data = users_collection.find_one({"_id": ObjectId(uid)})
    except Exception:
        user_data = None
    user_custom_categories = user_data.get("custom_categories", []) if user_data else []
    
    try:
        latest_expense = expenses_collection.find_one(
            {"user_id": uid, "type": "expense"}, sort=[("_id", -1)]
        )
    except Exception:
        latest_expense = None
    last_used_category = latest_expense.get("category", "") if latest_expense else ""
    
    today_date = datetime.now().strftime('%Y-%m-%d')
    active_tab = request.args.get('tab', 'expense')

    return render_template(
        "add.html",
        custom_categories=user_custom_categories,
        today_date=today_date,
        last_used_category=last_used_category,
        active_tab=active_tab
    )

@app.route("/view")
@login_required
def view():
    uid = session.get('user_id')
    filter_type = request.args.get('type', 'all').lower()

    query = {"user_id": uid}
    if filter_type in ['expense', 'income']:
        query["type"] = filter_type
    else:
        filter_type = 'all'

    try:
        expenses = list(expenses_collection.find(query).sort("date", -1))
    except Exception:
        expenses = []

    return render_template("view.html", expenses=expenses, filter_type=filter_type)

@app.route("/delete_custom_category")
@login_required
def delete_custom_category():
    uid = session.get('user_id')
    cat_name = request.args.get('name')
    
    if cat_name:
        try:
            users_collection.update_one(
                {"_id": ObjectId(uid)},
                {"$pull": {"custom_categories": cat_name}}
            )
            sync_local_db()
            flash(f"Category '{cat_name}' deleted successfully!", "success")
        except Exception:
            flash("Error deleting category.", "danger")
    
    return redirect(url_for("add"))

@app.route("/delete/<id>")
@login_required
def delete(id):
    try:
        expenses_collection.delete_one({"_id": ObjectId(id)})
        sync_local_db()
        flash("Record deleted successfully!", "success")
    except Exception:
        flash("Error deleting record.", "danger")
    return redirect(url_for("view"))

@app.route("/edit/<id>", methods=["GET", "POST"])
@login_required
def edit(id):
    try:
        oid = ObjectId(id)
    except Exception:
        flash("Invalid record ID!", "danger")
        return redirect(url_for("view"))

    if request.method == "POST":
        trans_type = request.form.get("type", "expense").lower()
        if trans_type not in ["expense", "income"]:
            trans_type = "expense"

        try:
            expenses_collection.update_one({"_id": oid}, {"$set": {
                "type": trans_type,
                "amount": float(request.form.get("amount", 0)),
                "category": request.form.get("category", "Other"),
                "date": request.form.get("date"),
                "description": request.form.get("description", "")
            }})
            flash("Record updated successfully!", "success")
        except Exception:
            flash("Error updating record.", "danger")
        return redirect(url_for("view"))

    try:
        expense = expenses_collection.find_one({"_id": oid})
    except Exception:
        expense = None
    return render_template("edit.html", expense=expense)

@app.route("/summary")
@login_required
def summary():
    uid = session.get('user_id')
    view_type = request.args.get('type', 'overall')
    if view_type not in ['overall', 'weekly', 'monthly', 'daily']:
        view_type = 'overall'
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    selected_category = request.args.get('category', '').strip()
    active_tab = request.args.get('tab', 'expense').lower()  # 'all', 'expense', 'income'

    try:
        transactions = list(expenses_collection.find({"user_id": uid}))
    except Exception:
        transactions = []

    now = datetime.now()
    one_week_ago = now - timedelta(days=7)

    # Initialize tracking structures for overall, weekly, monthly, daily
    timeframes = ['overall', 'weekly', 'monthly', 'daily']
    expense_data = {tf: {} for tf in timeframes}
    income_data = {tf: {} for tf in timeframes}
    income_totals = {tf: 0.0 for tf in timeframes}
    expense_totals = {tf: 0.0 for tf in timeframes}
    savings_totals = {tf: 0.0 for tf in timeframes}

    category_items = []
    is_cat_filtered = bool(selected_category and selected_category.lower() != 'all')

    for trans in transactions:
        amt = float(trans.get('amount', 0))
        cat = trans.get('category', 'Other')
        trans_type = trans.get('type', 'expense').lower()
        trans_date_str = trans.get('date', '')

        try:
            trans_date = datetime.strptime(trans_date_str, '%Y-%m-%d')
        except (TypeError, ValueError):
            continue

        tf_matches = {
            'overall': True,
            'weekly': (trans_date >= one_week_ago),
            'monthly': (trans_date.month == now.month and trans_date.year == now.year),
            'daily': (trans_date_str == selected_date)
        }

        for tf, matches in tf_matches.items():
            if matches:
                if trans_type == 'income':
                    income_totals[tf] += amt
                    income_data[tf][cat] = income_data[tf].get(cat, 0.0) + amt
                else:
                    expense_totals[tf] += amt
                    expense_data[tf][cat] = expense_data[tf].get(cat, 0.0) + amt

        if is_cat_filtered and cat.lower() == selected_category.lower():
            if tf_matches.get(view_type, False):
                category_items.append(trans)

    for tf in timeframes:
        savings_totals[tf] = income_totals[tf] - expense_totals[tf]

    total_income = income_totals['overall']
    total_expense = expense_totals['overall']
    total_saving = savings_totals['overall']
    saving_pct = round((total_saving / total_income * 100), 1) if total_income > 0 else 0.0
    expense_pct = round((total_expense / total_income * 100), 1) if total_income > 0 else 0.0

    totals = {
        'income': income_totals,
        'expense': expense_totals,
        'savings': savings_totals
    }

    category_items.sort(key=lambda x: x.get('date', ''), reverse=True)

    return render_template(
        "summary.html",
        expense_data=expense_data,
        income_data=income_data,
        totals=totals,
        income_totals=income_totals,
        expense_totals=expense_totals,
        total_income=total_income,
        total_expense=total_expense,
        total_saving=total_saving,
        saving_pct=saving_pct,
        expense_pct=expense_pct,
        selected_date=selected_date,
        view_type=view_type,
        active_tab=active_tab,
        selected_category=selected_category,
        category_items=category_items,
        is_category_filtered=is_cat_filtered
    )

@app.route("/summary/details")
@login_required
def summary_details():
    uid = session.get('user_id')
    category = request.args.get('category', '')
    view_type = request.args.get('type', 'overall')
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    expenses = list(expenses_collection.find({"user_id": uid, "category": category}))

    filtered = []
    total = 0
    filter_text = ''
    now = datetime.now()
    one_week_ago = now - timedelta(days=7)

    range_start = None
    range_end = None
    if from_date:
        try:
            range_start = datetime.strptime(from_date, '%Y-%m-%d')
        except ValueError:
            range_start = None
    if to_date:
        try:
            range_end = datetime.strptime(to_date, '%Y-%m-%d')
        except ValueError:
            range_end = None

    for exp in expenses:
        exp_date_str = exp.get('date')
        try:
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
        except:
            continue

        include = False
        if view_type == 'overall':
            include = True
            filter_text = 'Overall category breakdown'
        elif view_type == 'weekly':
            include = exp_date >= one_week_ago
            filter_text = 'Last 7 days'
        elif view_type == 'monthly':
            include = exp_date.month == now.month and exp_date.year == now.year
            filter_text = 'This month'
        elif view_type == 'daily':
            include = exp_date_str == selected_date
            filter_text = f'Date: {selected_date}'
        elif view_type == 'range':
            include = bool(range_start and range_end and range_start <= exp_date <= range_end)
            filter_text = f'{from_date} to {to_date}' if from_date and to_date else 'Custom range'

        if include:
            total += float(exp.get('amount', 0))
            filtered.append(exp)

    return render_template(
        'summary_details.html',
        category=category,
        expenses=filtered,
        total=total,
        filter_text=filter_text,
        view_type=view_type,
        selected_date=selected_date,
        from_date=from_date,
        to_date=to_date
    )
    
@app.route('/summary/report')
@login_required
def download_report():
    uid = session.get('user_id')
    view_type = request.args.get('type', 'overall')
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    selected_category = request.args.get('category', 'all').strip()

    items = list(expenses_collection.find({"user_id": uid}))

    now = datetime.now()
    one_week_ago = now - timedelta(days=7)

    is_cat_filtered = bool(selected_category and selected_category.lower() != 'all')

    filtered = []
    total_income = 0.0
    total_expense = 0.0

    for exp in items:
        exp_date_str = exp.get('date')
        cat = exp.get('category', 'Other')
        item_type = exp.get('type', 'expense').lower()
        if item_type != 'income':
            item_type = 'expense'
        try:
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
        except (TypeError, ValueError):
            continue

        if is_cat_filtered and cat.lower() != selected_category.lower():
            continue

        include = False
        if view_type == 'overall':
            include = True
        elif view_type == 'weekly':
            include = exp_date >= one_week_ago
        elif view_type == 'monthly':
            include = exp_date.month == now.month and exp_date.year == now.year
        elif view_type == 'daily':
            include = exp_date_str == selected_date

        if include:
            filtered.append(exp)
            amt = float(exp.get('amount', 0))
            if item_type == 'income':
                total_income += amt
            else:
                total_expense += amt

    filtered.sort(key=lambda e: e.get('date', ''))

    # Build PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Title'], textColor=colors.HexColor('#0284c7'), fontSize=18, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle', parent=styles['Normal'], textColor=colors.HexColor('#475569'), fontSize=9, spaceAfter=10
    )

    elements = []
    elements.append(Paragraph("Financial Tracker – Income & Expense Statement", title_style))

    user_name = session.get('first_name', 'User')
    generated_on = datetime.now().strftime('%d %b %Y, %I:%M %p')

    range_label = view_type.capitalize()
    if view_type == 'daily' and selected_date:
        range_label += f" ({selected_date})"
    elif view_type == 'monthly':
        range_label += " (Current Month)"
    elif view_type == 'weekly':
        range_label += " (Current Week)"

    elements.append(Paragraph(
        f"<b>User:</b> {user_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Report Period:</b> {range_label} "
        f"&nbsp;&nbsp;|&nbsp;&nbsp; <b>Generated:</b> {generated_on}",
        subtitle_style
    ))
    
    # Financial Overview Summary in PDF
    net_bal = total_income - total_expense
    summary_p = Paragraph(
        f"<b>Total Income:</b> <font color='#059669'>Rs {total_income:,.2f}</font> &nbsp;&nbsp;&nbsp;&nbsp; "
        f"<b>Total Expense:</b> <font color='#e11d48'>Rs {total_expense:,.2f}</font> &nbsp;&nbsp;&nbsp;&nbsp; "
        f"<b>Net Savings:</b> <font color='{'#059669' if net_bal >= 0 else '#e11d48'}'>Rs {net_bal:,.2f}</font>",
        ParagraphStyle('SummaryP', parent=styles['Normal'], fontSize=10, spaceAfter=12)
    )
    elements.append(summary_p)
    elements.append(Spacer(1, 4))

    table_data = [["#", "Date", "Type", "Category", "Description", "Amount (Rs)"]]
    for i, exp in enumerate(filtered, start=1):
        item_type = exp.get('type', 'expense').capitalize()
        table_data.append([
            str(i),
            exp.get('date', '-'),
            item_type,
            exp.get('category', '-'),
            exp.get('description', '') or '-',
            f"{float(exp.get('amount', 0)):,.2f}"
        ])

    if len(filtered) == 0:
        elements.append(Paragraph("No financial records found for this selection.", styles['Normal']))
    else:
        table = Table(table_data, colWidths=[20, 60, 55, 80, 185, 85], repeatRows=1)
        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]
        table.setStyle(TableStyle(style_commands))
        elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    filename = f"statement_{view_type}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(app.root_path, 'sitemap.xml')

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('dashboard' if 'user_id' in session else 'index'))

@app.errorhandler(500)
def internal_server_error(e):
    flash("An internal server error occurred. Please try again.", "danger")
    return redirect(url_for('dashboard' if 'user_id' in session else 'index'))

if __name__ == "__main__":
    app.run(debug=True)