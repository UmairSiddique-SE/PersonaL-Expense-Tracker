import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

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
@app.route("/", methods=["GET", "POST"])
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = users_collection.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            return redirect(url_for("dashboard"))
        flash("Invalid Credentials!", "danger")
    return render_template("auth.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Yahan apna login logic likhein (Database check)
        # Agar sahi hai to session['user_id'] = ... set karein
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # Yahan apna signup logic likhein (Database insert)
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/dashboard")
@login_required
def dashboard(): return render_template("index.html")

# --- EXPENSE ROUTES ---
@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        expenses_collection.insert_one({
            "user_id": session['user_id'],
            "amount": float(request.form.get("amount")),
            "category": request.form.get("category"),
            "date": request.form.get("date"),
            "description": request.form.get("description", "")
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
        flash("Expense updated successfully!", "success")
        return redirect(url_for("view"))
    expense = expenses_collection.find_one({"_id": ObjectId(id)})
    return render_template("edit.html", expense=expense)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")  
    return redirect(url_for("login"))
from datetime import datetime

from datetime import datetime, timedelta

@app.route("/summary")
@login_required
def summary():
    uid = session.get('user_id')
    view_type = request.args.get('type', 'overall')
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # User ke saare expenses fetch karein
    expenses = list(expenses_collection.find({"user_id": uid}))
    
    # Containers
    data = {"overall": {}, "weekly": {}, "monthly": {}, "daily": {}}
    totals = {"overall": 0, "weekly": 0, "monthly": 0, "daily": 0}
    
    now = datetime.now()
    one_week_ago = now - timedelta(days=7)
    
    for exp in expenses:
        amt = float(exp.get('amount', 0))
        cat = exp.get('category', 'Other')
        exp_date_str = exp.get('date')
        exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
        
        # 1. Overall logic
        data["overall"][cat] = data["overall"].get(cat, 0) + amt
        totals["overall"] += amt
        
        # 2. Weekly logic (Pichle 7 din)
        if exp_date >= one_week_ago:
            data["weekly"][cat] = data["weekly"].get(cat, 0) + amt
            totals["weekly"] += amt
            
        # 3. Monthly logic (Current month)
        if exp_date.month == now.month and exp_date.year == now.year:
            data["monthly"][cat] = data["monthly"].get(cat, 0) + amt
            totals["monthly"] += amt
            
        # 4. Daily logic (Calendar filter)
        if exp_date_str == selected_date:
            data["daily"][cat] = data["daily"].get(cat, 0) + amt
            totals["daily"] += amt
            
    return render_template("summary.html", 
                           view_type=view_type, 
                           data=data, 
                           totals=totals, 
                           selected_date=selected_date)