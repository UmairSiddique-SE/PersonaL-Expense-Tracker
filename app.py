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
            # Pura naam session mein store karein
            session['user_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            return redirect(url_for("dashboard"))
        flash("Invalid Credentials!", "danger")
    return render_template("auth.html")

@app.route("/signup", methods=["POST"])
def signup():
    # Naye fields fetch karein
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    username = request.form.get("username")
    password = request.form.get("password")
    
    if "@" not in username or "." not in username or len(password) < 8:
        flash("Invalid email or password (min 8 chars)!", "danger")
        return redirect(url_for("login"))
        
    if users_collection.find_one({"username": username}):
        flash("User already exists!", "danger")
        return redirect(url_for("login"))

    # DB mein save karein
    user = {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "password": generate_password_hash(password)
    }
    users_collection.insert_one(user)
    flash("Account created! Please login.", "success")
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("index.html")

# --- OTHER ROUTES (Add, View, Delete, PWA) ---
@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        try:
            # Check karte hain ki data aa raha hai ya nahi
            amount_str = request.form.get("amount")
            category = request.form.get("category")
            date = request.form.get("date")
            description = request.form.get("description", "")
            
            if not amount_str or not category or not date:
                flash("All fields are required!", "danger")
                return redirect(url_for("add"))
            
            expenses_collection.insert_one({
                "user_id": session['user_id'],
                "amount": float(amount_str),
                "category": category,
                "date": date,
                "description": description
            })
            return redirect(url_for("view"))
        except Exception as e:
            print(f"ERROR: {e}") # Terminal mein error dikhayega
            flash("Error saving expense. Please check your input.", "danger")
            return redirect(url_for("add"))
            
    return render_template("add.html")

@app.route("/view")
@login_required
def view():
    expenses = list(expenses_collection.find({"user_id": session['user_id']}))
    return render_template("view.html", expenses=expenses)

@app.route("/delete/<id>")
@login_required
def delete(id):
    expenses_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for("view"))

@app.route('/sw.js')
def serve_sw(): return send_from_directory('static', 'sw.js')

@app.route('/manifest.json')
def serve_manifest(): return send_from_directory('static', 'manifest.json')

if __name__ == "__main__":
    app.run(debug=True)