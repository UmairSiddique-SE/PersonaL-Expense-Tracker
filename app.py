import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "expense_secret_key"

# MongoDB Connection
client = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/"))
db = client['expense_db']
expenses_collection = db['expenses']
users_collection = db['users']

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
        
        user = users_collection.find_one({"username": username})
        
        if user and check_password_hash(user['password'], password):
            # Session mein user_id aur first_name dono save karein
            session['user_id'] = str(user['_id'])
            session['first_name'] = user.get('first_name', 'User') # <--- Ye line add hui
            
            return redirect(url_for("dashboard"))
        
        flash("Invalid Username or Password!", "danger")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        
        raw_username = request.form.get("username")
        username = raw_username.lower().strip() if raw_username else ""
        password = request.form.get("password")
        security_question = request.form.get("security_question", "").strip()
        security_answer = request.form.get("security_answer", "").strip()
        
        if not username or not password or not security_question or not security_answer:
            flash("All fields are required!", "danger")
            return redirect(url_for("signup"))
        
        if users_collection.find_one({"username": username}):
            flash("User already exists! Please login.", "danger")
            return redirect(url_for("signup"))
        
        hashed_pw = generate_password_hash(password)
        users_collection.insert_one({
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "password": hashed_pw,
            "security_question": security_question,
            "security_answer": security_answer.lower()
        })
        
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

        user = users_collection.find_one({"username": username})
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

# --- DASHBOARD & EXPENSE ROUTes ---
@app.route("/dashboard")
@login_required
def dashboard(): 
    return render_template("dashboard.html")

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")
        date = request.form.get("date")
        description = request.form.get("description", "")
        
        # MongoDB database mein expense save karna
        expenses_collection.insert_one({
            "user_id": session['user_id'],
            "amount": float(amount) if amount else 0.0,
            "category": category,
            "date": date,
            "description": description
        })
        flash("Expense added successfully!", "success")
        return redirect(url_for("add"))
        
    return render_template("add.html")

@app.route("/view")
@login_required
def view():
    expenses = list(expenses_collection.find({"user_id": session.get('user_id')}))
    return render_template("view.html", expenses=expenses)

@app.route("/delete/<id>")
@login_required
def delete(id):
    expenses_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for("view"))

@app.route("/edit/<id>", methods=["GET", "POST"])
@login_required
def edit(id):
    if request.method == "POST":
        expenses_collection.update_one({"_id": ObjectId(id)}, {"$set": {
            "amount": float(request.form.get("amount")),
            "category": request.form.get("category"),
            "date": request.form.get("date"),
            "description": request.form.get("description")
        }})
        return redirect(url_for("view"))
    expense = expenses_collection.find_one({"_id": ObjectId(id)})
    return render_template("edit.html", expense=expense)

@app.route("/summary")
@login_required
def summary():
    uid = session.get('user_id')
    view_type = request.args.get('type', 'overall')
    if view_type not in ['overall', 'weekly', 'monthly', 'daily']:
        view_type = 'overall'
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    expenses = list(expenses_collection.find({"user_id": uid}))
    
    data = {"overall": {}, "weekly": {}, "monthly": {}, "daily": {}}
    totals = {"overall": 0, "weekly": 0, "monthly": 0, "daily": 0}
    now = datetime.now()
    one_week_ago = now - timedelta(days=7)
    
    for exp in expenses:
        amt = float(exp.get('amount', 0))
        cat = exp.get('category', 'Other')
        exp_date_str = exp.get('date')
        try:
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
        except:
            continue
        
        data["overall"][cat] = data["overall"].get(cat, 0) + amt
        totals["overall"] += amt
        if exp_date >= one_week_ago:
            data["weekly"][cat] = data["weekly"].get(cat, 0) + amt
            totals["weekly"] += amt
        if exp_date.month == now.month and exp_date.year == now.year:
            data["monthly"][cat] = data["monthly"].get(cat, 0) + amt
            totals["monthly"] += amt
        if exp_date_str == selected_date:
            data["daily"][cat] = data["daily"].get(cat, 0) + amt
            totals["daily"] += amt
            
    return render_template(
        "summary.html",
        data=data,
        totals=totals,
        selected_date=selected_date,
        view_type=view_type
    )

if __name__ == "__main__":
    app.run(debug=True)