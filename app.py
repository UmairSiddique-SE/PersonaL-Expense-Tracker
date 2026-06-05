



#                                       new code
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson.objectid import ObjectId
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "expense_secret_key"

# MongoDB Connection
client = MongoClient(os.environ.get("MONGO_URI"))
db = client['expense_db']
expenses_collection = db['expenses']

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        expense = {
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
def view():
    expenses = list(expenses_collection.find())
    return render_template("view.html", expenses=expenses)

@app.route("/edit/<id>", methods=["GET", "POST"])
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
def delete(id):
    expenses_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for("view"))

@app.route("/summary")
def summary():
    view_type = request.args.get("type", "overall")
    today = datetime.today()
    all_expenses = list(expenses_collection.find())
    
    # Data aur Totals ke liye containers
    data = {"overall": {}, "weekly": {}, "monthly": {}}
    totals = {"overall": 0, "weekly": 0, "monthly": 0}

    for e in all_expenses:
        try:
            amount = float(e.get("amount", 0))
            category = e.get("category", "Other")
            expense_date = datetime.strptime(e.get("date"), "%Y-%m-%d")
            
            # Logic for Overall
            data["overall"][category] = data["overall"].get(category, 0) + amount
            totals["overall"] += amount
            
            # Logic for Weekly (Last 7 days)
            if today - timedelta(days=7) <= expense_date <= today:
                data["weekly"][category] = data["weekly"].get(category, 0) + amount
                totals["weekly"] += amount
            
            # Logic for Monthly (Current month)
            if expense_date.month == today.month and expense_date.year == today.year:
                data["monthly"][category] = data["monthly"].get(category, 0) + amount
                totals["monthly"] += amount
        except: 
            continue
    
    return render_template(
        "summary.html",
        data=data,          # Isme overall, weekly, monthly ka data hai
        totals=totals,      # Isme 3no ka total hai
        view_type=view_type
    )


if __name__ == "__main__":
    app.run(debug=True)
