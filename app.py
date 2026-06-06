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
@app.route("/", methods=["GET", "POST"])
def login():
    if 'user_id' in session: 
        return redirect(url_for('index'))
    if request.method == "POST":
        user = users_collection.find_one({"username": request.form["username"]})
        if user and check_password_hash(user['password'], request.form["password"]):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user.get('username', 'User')
            return redirect(url_for("index"))
        flash("Invalid Credentials", "danger")
    return render_template("auth.html")

@app.route("/signup", methods=["POST"])
def signup():
    username = request.form["username"]
    if users_collection.find_one({"username": username}):
        flash("User already exists!", "danger")
        return redirect(url_for("login"))
    user = {
        "username": username,
        "password": generate_password_hash(request.form["password"])
    }
    users_collection.insert_one(user)
    flash("Account created! Please login.", "success")
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- APP ROUTES ---
@app.route("/dashboard")
@login_required
def index():
    return render_template("index.html")

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        expense = {
            "user_id": session['user_id'],
            "amount": float(request.form["amount"]),
            "category": request.form["category"],
            "date": request.form["date"],
            "description": request.form["description"]
        }
        expenses_collection.insert_one(expense)
        return redirect(url_for("view"))
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

# --- PWA & STATIC ---
@app.route('/sw.js')
def serve_sw(): return send_from_directory('static', 'sw.js')

@app.route('/manifest.json')
def serve_manifest(): return send_from_directory('static', 'manifest.json')

if __name__ == "__main__":
    app.run(debug=True)