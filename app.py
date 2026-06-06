import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from datetime import datetime, timedelta
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

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- AUTH ROUTES ---
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        if users_collection.find_one({"username": username}):
            flash("User already exists!", "danger")
            return redirect(url_for("signup"))
        
        user = {
            "first_name": request.form["first_name"],
            "last_name": request.form["last_name"],
            "username": username,
            "password": generate_password_hash(request.form["password"])
        }
        users_collection.insert_one(user)
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = users_collection.find_one({"username": request.form["username"]})
        if user and check_password_hash(user['password'], request.form["password"]):
            session['user_id'] = str(user['_id'])
            session['user_name'] = f"{user['first_name']} {user['last_name']}"
            return redirect(url_for("index"))
        flash("Invalid Credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- PWA ROUTES ---
@app.route('/sw.js')
def serve_sw(): return send_from_directory('static', 'sw.js')

@app.route('/manifest.json')
def serve_manifest(): return send_from_directory('static', 'manifest.json')

# --- EXPENSE ROUTES ---
@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        expense = {
            "user_id": session['user_id'],
            "amount": request.form["amount"],
            "category": request.form["category"],
            "date": request.form["date"],
            "description": request.form["description"]
        }
        expenses_collection.insert_one(expense)
        flash("Expense added successfully 👍", "success")
        return redirect(url_for("add"))
    return render_template("add.html")

@app.route("/view")
@login_required
def view():
    expenses = list(expenses_collection.find({"user_id": session['user_id']}))
    return render_template("view.html", expenses=expenses)

@app.route("/edit/<id>", methods=["GET", "POST"])
@login_required
def edit(id):
    if request.method == "POST":
        expenses_collection.update_one({"_id": ObjectId(id)}, {"$set": {
            "amount": request.form["amount"],
            "category": request.form["category"],
            "date": request.form["date"],
            "description": request.form["description"]
        }})
        return redirect(url_for("view"))
    expense = expenses_collection.find_one({"_id": ObjectId(id)})
    return render_template("edit.html", expense=expense, id=id)

@app.route("/delete/<id>")
@login_required
def delete(id):
    expenses_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for("view"))

@app.route("/summary")
@login_required
def summary():
    view_type = request.args.get("type", "overall")
    today = datetime.today()
    all_expenses = list(expenses_collection.find({"user_id": session['user_id']}))
    
    data = {"overall": {}, "weekly": {}, "monthly": {}}
    totals = {"overall": 0, "weekly": 0, "monthly": 0}

    for e in all_expenses:
        try:
            amount = float(e.get("amount", 0))
            category = e.get("category", "Other")
            expense_date = datetime.strptime(e.get("date"), "%Y-%m-%d")
            data["overall"][category] = data["overall"].get(category, 0) + amount
            totals["overall"] += amount
            if today - timedelta(days=7) <= expense_date <= today:
                data["weekly"][category] = data["weekly"].get(category, 0) + amount
                totals["weekly"] += amount
            if expense_date.month == today.month and expense_date.year == today.year:
                data["monthly"][category] = data["monthly"].get(category, 0) + amount
                totals["monthly"] += amount
        except: continue
    return render_template("summary.html", data=data, totals=totals, view_type=view_type)

if __name__ == "__main__":
    app.run(debug=True)