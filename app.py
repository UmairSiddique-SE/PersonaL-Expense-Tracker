# from flask import Flask, render_template, request, redirect, url_for, flash     # Flask framework
# from datetime import datetime, timedelta     # Date handling
# import csv, os       # CSV and OS operations
# import matplotlib.pyplot as plt    # For chart generation
# # FLASK APP SETUP   
# app = Flask(__name__)
# app.secret_key = "expense_secret_key"
# # FILENAME = "expenses.csv"

# # # CREATE CSV IF NOT EXISTS
# # if not os.path.exists(FILENAME):
# #     with open(FILENAME, "w", newline="") as f:
# #         writer = csv.writer(f)
# #         writer.writerow(["Amount", "Category", "Date", "Description"])
# # # HOME ROUTE
# @app.route("/")
# def index():
#     return render_template("index.html")
# # ADD EXPENSE
# @app.route("/add", methods=["GET", "POST"])
# def add():
#     if request.method == "POST":
#         amount = request.form["amount"]
#         category = request.form["category"]
#         date = request.form["date"]
#         description = request.form["description"]

#         if not amount or not date:
#             flash("Amount & Date required ", "error")
#             return redirect(url_for("add"))

#         with open(FILENAME, "a", newline="") as f:
#             writer = csv.writer(f)
#             writer.writerow([amount, category, date, description])

#         flash("Expense added successfully 👍", "success")
#         return redirect(url_for("add"))

#     return render_template("add.html")

# # VIEW EXPENSES
# @app.route("/view")
# def view():
    
#     expenses = []
#     with open(FILENAME, "r") as f:
#         reader = csv.reader(f)
#         next(reader)
#         for i, row in enumerate(reader):
#             expenses.append({
#                 "id": i,
#                 "amount": row[0],
#                 "category": row[1],
#                 "date": row[2],
#                 "description": row[3]
#             })
#     return render_template("view.html", expenses=expenses)

# # EDIT EXPENSE
# @app.route("/edit/<int:id>", methods=["GET", "POST"])
# def edit(id):
#     with open(FILENAME, "r") as f:
#         rows = list(csv.reader(f))

#     if id + 1 >= len(rows):
#         flash("Expense not found! ", "error")
#         return redirect(url_for("view"))
    
#     expense = rows[id + 1]

#     if request.method == "POST":
#         rows[id + 1] = [
#             request.form["amount"],
#             request.form["category"],
#             request.form["date"],
#             request.form["description"]
#         ]
#         with open(FILENAME, "w", newline="") as f:
#             writer = csv.writer(f)
#             writer.writerows(rows)
#         # flash("Expense updated 👍", "success")
#         return redirect(url_for("view"))
#     return render_template("edit.html", expense=expense, id=id)

# # DELETE EXPENSE
# @app.route("/delete/<int:id>")
# def delete(id):
#     with open(FILENAME, "r") as f:
#         rows = list(csv.reader(f))

#     if id + 1 >= len(rows):
#         flash("Expense not found!", "error")
#         return redirect(url_for("view"))
    
#     rows.pop(id + 1)

#     with open(FILENAME, "w", newline="") as f:
#         writer = csv.writer(f)
#         writer.writerows(rows)

#     # flash("Expense deleted 👍", "success")
#     return redirect(url_for("view"))

# # SUMMARY (OVERALL / WEEKLY / MONTHLY) WITH DATE SELECTION
# @app.route("/summary")
# def summary():
#     view_type = request.args.get("type")  # overall / week / month
#     today = datetime.today()

#     overall = {}
#     weekly = {}
#     monthly = {}

#     with open(FILENAME, "r") as f:
#         reader = csv.reader(f)
#         next(reader)

#         for row in reader:
#             try:
#                 amount = float(row[0])
#                 category = row[1] if row[1] else "Other"
#                 date = datetime.strptime(row[2], "%Y-%m-%d")
#             except:
#                 continue

#             # OVERALL (All time)
#             overall[category] = overall.get(category, 0) + amount

#             # WEEKLY (Last 7 days)
#             if today - timedelta(days=7) <= date <= today:
#                 weekly[category] = weekly.get(category, 0) + amount

#             # MONTHLY (Current month)
#             if date.month == today.month and date.year == today.year:
#                 monthly[category] = monthly.get(category, 0) + amount

#     # Chart data select
#     chart_data = overall
#     title = "Overall Expense Summary"

#     if view_type == "week":
#         chart_data = weekly
#         title = "Weekly Expense Summary (Last 7 Days)"
#     elif view_type == "month":
#         chart_data = monthly
#         title = "Monthly Expense Summary (Current Month)"

#     chart_file = None
#     if chart_data:
#         plt.figure(figsize=(6,6))
#         plt.pie(
#             chart_data.values(),
#             labels=chart_data.keys(),
#             autopct="%1.1f%%",
#             startangle=140,
#             colors=plt.cm.Paired.colors
#         )
#         plt.title(title)
#         chart_file = "static/chart.png"
#         plt.savefig(chart_file, transparent=True, bbox_inches="tight")
#         plt.close()

#     return render_template(
#         "summary.html",
#         overall=overall,
#         weekly=weekly,
#         monthly=monthly,
#         chart_file=chart_file,
#         view_type=view_type
#     )


# # RUN
# if __name__ == "__main__":
#     app.run(debug=True)
#     # app.run(host="0.0.0.0", port=5000)





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
