import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
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

# Root route login page ke liye
@app.route("/", methods=["GET", "POST"])
def login():
    if 'user_id' in session: 
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = users_collection.find_one({"username": username})
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            return redirect(url_for("dashboard"))
        
        flash("Invalid Credentials!", "danger")
    return render_template("login.html") # Yahan apna login template ka naam ensure karein

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # Yahan apna signup logic (generate_password_hash use karein)
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/dashboard")
@login_required
def dashboard(): 
    return render_template("index.html")

# --- EXPENSE ROUTES ---
# (Baaki routes wahi rahenge jo aapne likhe the, wo sahi hain)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- SUMMARY ROUTE ---
@app.route("/summary")
@login_required
def summary():
    uid = session.get('user_id')
    view_type = request.args.get('type', 'overall')
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
            
    return render_template("summary.html", view_type=view_type, data=data, 
                           totals=totals, selected_date=selected_date)

if __name__ == "__main__":
    app.run(debug=True)