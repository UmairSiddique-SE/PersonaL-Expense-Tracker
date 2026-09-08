import io
import os
import re
import secrets
from hmac import compare_digest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps
from xml.sax.saxutils import escape

from bson.objectid import ObjectId
from flask import Flask, flash, redirect, render_template, request, send_file, send_from_directory, session, url_for
from pymongo import MongoClient
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from werkzeug.security import check_password_hash, generate_password_hash

from accounting import normalize_transaction_type

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")
app.permanent_session_lifetime = timedelta(days=30)
app.config.update(SEND_FILE_MAX_AGE_DEFAULT=31536000, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1")
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
        expenses_collection.create_index([("user_id", 1), ("type", 1), ("date", -1)], name="user_type_date")
    except Exception as exc: app.logger.warning("Database indexes could not be created: %s", exc)
ensure_indexes()

@app.before_request
def csrf_protect():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        token = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
        expected = session.get("_csrf_token")
        if not expected or not token or not compare_digest(token, expected): return ("CSRF validation failed.", 400)

@app.context_processor
def inject_csrf_token():
    def csrf_token():
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32); session["_csrf_token"] = token
        return token
    return {"csrf_token": csrf_token}

def utc_now(): return datetime.now(timezone.utc)

def parse_amount(value):
    try:
        amount = Decimal(str(value or "").strip().replace(",", ""))
        if not amount.is_finite() or amount <= 0: raise ValueError
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError): raise ValueError("Amount must be a valid number greater than 0.")

def money(value):
    try: return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError): return Decimal("0.00")

def parse_record_date(value):
    try: return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError): raise ValueError("Please enter a valid date.")

def normalize_text(value, max_length=500): return re.sub(r"\s+", " ", str(value or "").strip())[:max_length]
def normalize_category(value, default="Other"):
    value = normalize_text(value, 80); return value if value else default

def safe_object_id(value):
    try: return ObjectId(value)
    except Exception: return None

def record_created_at(record):
    value = record.get("created_at")
    if isinstance(value, datetime): return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00")); return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        except ValueError: pass
    oid = record.get("_id")
    if isinstance(oid, ObjectId): return oid.generation_time
    return datetime.min.replace(tzinfo=timezone.utc)

def sort_by_added(records, newest_first=True): return sorted(records, key=record_created_at, reverse=newest_first)
def record_to_view(record):
    item = dict(record); item["amount"] = float(money(item.get("amount"))); item["type"] = normalize_transaction_type(item.get("type")); return item

def shift_months(year, month, offset):
    index = year * 12 + (month - 1) + offset; return index // 12, index % 12 + 1

def last_six_months(today=None):
    today = today or date.today(); result=[]
    for offset in range(-5,1):
        year, month = shift_months(today.year,today.month,offset); result.append((year,month,date(year,month,1).strftime("%b %Y")))
    return result

def transaction_date(record):
    try: return parse_record_date(record.get("date"))
    except ValueError: return None

def login_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"): return redirect(url_for("login"))
        return view_function(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    if request.args.get("source") == "pwa": return redirect(url_for("dashboard" if session.get("user_id") else "login"))
    return render_template("index.html")
@app.route("/index")
def index_alias(): return redirect(url_for("index"))
@app.route("/sw.js")
def service_worker(): return send_from_directory(app.root_path,"sw.js")

@app.route("/login", methods=["GET","POST"])
def login():
    if session.get("user_id"): return redirect(url_for("dashboard"))
    if request.method=="POST":
        username=normalize_text(request.form.get("username"),120).lower(); password=request.form.get("password","")
        if not username or not password: flash("Username and password are required.","danger"); return render_template("login.html")
        try: user=users_collection.find_one({"username":username})
        except Exception: app.logger.exception("Login database error"); flash("Database connection error. Please try again.","danger"); return render_template("login.html")
        if user:
            try: password_valid=bool(user.get("password")) and check_password_hash(user.get("password",""),password)
            except (ValueError,TypeError): password_valid=False
            if password_valid:
                session.clear(); session.permanent=bool(request.form.get("remember_me")); session["user_id"]=str(user["_id"]); session["first_name"]=user.get("first_name","User"); return redirect(url_for("dashboard"))
        flash("Invalid username or password.","danger")
    return render_template("login.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method=="POST":
        first_name=normalize_text(request.form.get("first_name"),80); username=normalize_text(request.form.get("username"),120).lower(); password=request.form.get("password",""); security_question=normalize_text(request.form.get("security_question"),200); security_answer=normalize_text(request.form.get("security_answer"),200).lower()
        if not first_name or not username or not password or not security_question or not security_answer: flash("All fields are required.","danger"); return redirect(url_for("signup"))
        if len(username)<3: flash("Username must be at least 3 characters.","danger"); return redirect(url_for("signup"))
        if len(password)<8: flash("Password must be at least 8 characters.","danger"); return redirect(url_for("signup"))
        try:
            if users_collection.find_one({"username":username}): flash("User already exists. Please login.","danger"); return redirect(url_for("signup"))
            users_collection.insert_one({"first_name":first_name,"username":username,"password":generate_password_hash(password),"security_question":security_question,"security_answer":generate_password_hash(security_answer),"custom_categories":[],"created_at":utc_now()})
        except Exception: app.logger.exception("Signup database error"); flash("Unable to create the account. Please try again.","danger"); return redirect(url_for("signup"))
        flash("Signup successful! Please login.","success"); return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/forgot", methods=["GET","POST"])
def forgot():
    if request.method=="POST":
        step=request.form.get("step","lookup"); username=normalize_text(request.form.get("username"),120).lower()
        if not username: flash("Please enter your registered username.","danger"); return render_template("forgot.html")
        try: user=users_collection.find_one({"username":username})
        except Exception: app.logger.exception("Password reset database error"); flash("Database connection error.","danger"); return render_template("forgot.html")
        if not user: flash("Invalid username.","danger"); return render_template("forgot.html")
        question=user.get("security_question")
        if not question: flash("No recovery question is configured for this account.","danger"); return render_template("forgot.html")
        if step=="lookup": return render_template("forgot.html",step="question",username=username,question=question)
        security_answer=normalize_text(request.form.get("security_answer"),200).lower(); new_password=request.form.get("new_password",""); stored_answer=user.get("security_answer","")
        try: valid_answer=check_password_hash(stored_answer,security_answer)
        except (ValueError,TypeError): valid_answer=security_answer==str(stored_answer).lower()
        if not valid_answer: flash("Security answer does not match.","danger"); return render_template("forgot.html",step="question",username=username,question=question)
        if len(new_password)<8: flash("New password must be at least 8 characters.","danger"); return render_template("forgot.html",step="question",username=username,question=question)
        try: users_collection.update_one({"_id":user["_id"]},{"$set":{"password":generate_password_hash(new_password)}})
        except Exception: app.logger.exception("Password reset update error"); flash("Unable to reset password. Please try again.","danger"); return render_template("forgot.html",step="question",username=username,question=question)
        flash("Password reset successful. Please login.","success"); return redirect(url_for("login"))
    return render_template("forgot.html")

@app.route("/logout",methods=["POST"])
def logout(): session.clear(); return redirect(url_for("index"))

@app.route("/settings")
@login_required
def settings():
    oid=safe_object_id(session.get("user_id"))
    if not oid: session.clear(); return redirect(url_for("login"))
    try: user=users_collection.find_one({"_id":oid})
    except Exception: user=None
    if not user: session.clear(); return redirect(url_for("login"))
    return render_template("settings.html",user=user)
@app.route("/update_name",methods=["POST"])
@login_required
def update_name():
    oid=safe_object_id(session.get("user_id")); first_name=normalize_text(request.form.get("first_name"),80)
    if not oid or not first_name: flash("Name cannot be empty.","danger"); return redirect(url_for("settings"))
    try: users_collection.update_one({"_id":oid},{"$set":{"first_name":first_name}}); session["first_name"]=first_name; flash("Name updated successfully.","success")
    except Exception: app.logger.exception("Name update error"); flash("Error updating name.","danger")
    return redirect(url_for("settings"))
@app.route("/change_password",methods=["POST"])
@login_required
def change_password():
    oid=safe_object_id(session.get("user_id")); current_pw=request.form.get("current_password",""); new_pw=request.form.get("new_password",""); confirm_pw=request.form.get("confirm_password","")
    try: user=users_collection.find_one({"_id":oid}) if oid else None
    except Exception: user=None
    if not user or not check_password_hash(user.get("password",""),current_pw): flash("Incorrect current password.","danger"); return redirect(url_for("settings"))
    if len(new_pw)<8: flash("New password must be at least 8 characters long.","danger"); return redirect(url_for("settings"))
    if new_pw!=confirm_pw: flash("New passwords do not match.","danger"); return redirect(url_for("settings"))
    users_collection.update_one({"_id":oid},{"$set":{"password":generate_password_hash(new_pw)}}); session.clear(); flash("Password updated successfully. Please login again.","success"); return redirect(url_for("login"))
@app.route("/delete_account",methods=["POST"])
@login_required
def delete_account():
    oid=safe_object_id(session.get("user_id")); password=request.form.get("confirm_delete_password","")
    try:
        user=users_collection.find_one({"_id":oid}) if oid else None
        if not user or not check_password_hash(user.get("password",""),password): flash("Incorrect password. Account deletion cancelled.","danger"); return redirect(url_for("settings"))
        expenses_collection.delete_many({"user_id":str(oid)}); users_collection.delete_one({"_id":oid})
    except Exception: app.logger.exception("Account deletion error"); flash("Account could not be deleted. Please try again.","danger"); return redirect(url_for("settings"))
    session.clear(); flash("Your account and associated records have been permanently deleted.","success"); return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    uid=session.get("user_id")
    try: transactions=list(expenses_collection.find({"user_id":uid}))
    except Exception: app.logger.exception("Dashboard query error"); transactions=[]
    today=date.today(); total_income=Decimal("0"); total_expense=Decimal("0"); month_income=Decimal("0"); month_expense=Decimal("0"); lent=Decimal("0"); returned=Decimal("0"); receivable=Decimal("0"); loan_received=Decimal("0"); loan_repaid=Decimal("0");
    expense_category_totals={}; income_category_totals={}; six_months=last_six_months(today); month_keys=[f"{y:04d}-{m:02d}" for y,m,_ in six_months]; month_labels=[label for _,_,label in six_months]; chart_income_map={key:Decimal("0") for key in month_keys}; chart_expense_map={key:Decimal("0") for key in month_keys}
    for item in transactions:
        amount=money(item.get("amount")); t=normalize_transaction_type(item.get("type")); category=normalize_category(item.get("category")); td=transaction_date(item)
        if t=="income": total_income+=amount; income_category_totals[category]=income_category_totals.get(category,Decimal("0"))+amount
        elif t=="expense": total_expense+=amount; expense_category_totals[category]=expense_category_totals.get(category,Decimal("0"))+amount
        elif t=="money_lent": lent+=amount
        elif t=="money_returned": returned+=amount
        elif t=="loan_received": loan_received+=amount
        elif t=="loan_repayment": loan_repaid+=amount
        if td:
            key=td.strftime("%Y-%m")
            if td.year==today.year and td.month==today.month:
                if t=="income": month_income+=amount
                elif t=="expense": month_expense+=amount
            if key in chart_income_map:
                if t=="income": chart_income_map[key]+=amount
                elif t=="expense": chart_expense_map[key]+=amount
    total_savings=total_income-total_expense; month_savings=month_income-month_expense; saving_pct=round(total_savings/total_income*100,1) if total_income>0 else 0; expense_pct=round(total_expense/total_income*100,1) if total_income>0 else 0; top_expense_category=max(expense_category_totals,key=expense_category_totals.get) if expense_category_totals else "None"; top_income_source=max(income_category_totals,key=income_category_totals.get) if income_category_totals else "None"
    receivable=max(lent-returned,Decimal("0")); payable=max(loan_received-loan_repaid,Decimal("0")); cash_net=total_income+returned+loan_received-total_expense-lent-loan_repaid
    return render_template("dashboard.html",total_income=float(total_income),total_expense=float(total_expense),total_savings=float(total_savings),total_saving=float(total_savings),total_balance=float(total_savings),month_income=float(month_income),month_expense=float(month_expense),month_savings=float(month_savings),month_saving=float(month_savings),month_balance=float(month_savings),total_records=len(transactions),top_category=top_expense_category,top_expense_category=top_expense_category,top_income_source=top_income_source,saving_pct=float(saving_pct),expense_pct=float(expense_pct),chart_labels=month_labels,chart_income_data=[float(chart_income_map[k]) for k in month_keys],chart_expense_data=[float(chart_expense_map[k]) for k in month_keys],money_lent=float(lent),money_returned=float(returned),receivable_outstanding=float(receivable),loan_received=float(loan_received),loan_repaid=float(loan_repaid),payable_outstanding=float(payable),cash_net=float(cash_net))

@app.route("/add",methods=["GET","POST"])
@login_required
def add():
    uid=session.get("user_id")
    if request.method=="POST":
        record_type=normalize_transaction_type(request.form.get("record_type"),"expense")
        try: amount=parse_amount(request.form.get("amount")); record_date=parse_record_date(request.form.get("date"))
        except ValueError as exc: flash(str(exc),"danger"); return redirect(url_for("add")+f"?tab={record_type}")
        description=normalize_text(request.form.get("description"),500); category=normalize_category(request.form.get("category"),"Income" if record_type=="income" else "Other"); party=normalize_text(request.form.get("party"),120); account=normalize_text(request.form.get("account"),80) or "Cash"; reference=normalize_text(request.form.get("reference"),100)
        if record_type=="expense" and request.form.get("category")=="custom": category=normalize_category(request.form.get("custom_category"),"Other")
        if record_type in {"money_lent","money_returned","loan_received","loan_repayment"} and not party: flash("Person / Party is required for this transaction type.","danger"); return redirect(url_for("add")+f"?tab={record_type}")
        if record_type=="transfer_in" and not request.form.get("from_account"): flash("Source account is required for a transfer.","danger"); return redirect(url_for("add")+"?tab=transfer_in")
        if record_type=="transfer_out" and not request.form.get("to_account"): flash("Destination account is required for a transfer.","danger"); return redirect(url_for("add")+"?tab=transfer_out")
        if record_type=="expense" and request.form.get("category")=="custom":
            try: users_collection.update_one({"_id":ObjectId(uid)},{"$addToSet":{"custom_categories":category}})
            except Exception: app.logger.warning("Could not save custom category",exc_info=True)
        try:
            now=utc_now(); expenses_collection.insert_one({"user_id":uid,"type":record_type,"amount":float(amount),"category":category,"date":record_date.isoformat(),"description":description,"party":party,"account":account,"reference":reference,"from_account":normalize_text(request.form.get("from_account"),80),"to_account":normalize_text(request.form.get("to_account"),80),"created_at":now,"updated_at":now})
            flash(f"{record_type.replace('_',' ').capitalize()} added successfully!","success")
        except Exception: app.logger.exception("Record insert error"); flash("Database error saving record.","danger")
        return redirect(url_for("add")+f"?tab={record_type}")
    try: user_data=users_collection.find_one({"_id":ObjectId(uid)})
    except Exception: user_data=None
    custom_categories=user_data.get("custom_categories",[]) if user_data else []
    try: latest=expenses_collection.find_one({"user_id":uid,"type":"expense"},sort=[("created_at",-1),("_id",-1)])
    except Exception: latest=None
    return render_template("add.html",custom_categories=custom_categories,today_date=date.today().isoformat(),last_used_category=latest.get("category","") if latest else "",active_tab=request.args.get("tab","expense"))

@app.route("/view")
@login_required
def view():
    uid=session.get("user_id"); filter_type=request.args.get("type","all").strip().lower(); valid={"all","expense","income","money_lent","money_returned","loan_received","loan_repayment","transfer_in","transfer_out","adjustment"}; filter_type=filter_type if filter_type in valid else "all"; query={"user_id":uid}
    if filter_type!="all": query["type"]=filter_type
    try: expenses=[record_to_view(item) for item in expenses_collection.find(query).sort([("created_at",-1),("_id",-1)])]; expenses=sort_by_added(expenses,True)
    except Exception: app.logger.exception("View records query error"); flash("Unable to load your records right now. Please refresh and try again.","danger"); expenses=[]
    return render_template("view.html",expenses=expenses,filter_type=filter_type)

@app.route("/delete_custom_category",methods=["POST"])
@login_required
def delete_custom_category():
    uid=session.get("user_id"); cat_name=normalize_text(request.form.get("name") or request.args.get("name"),80)
    if cat_name:
        try: users_collection.update_one({"_id":ObjectId(uid)},{"$pull":{"custom_categories":cat_name}}); flash(f"Category '{cat_name}' deleted successfully!","success")
        except Exception: app.logger.exception("Custom category deletion error"); flash("Error deleting category.","danger")
    return redirect(url_for("add"))

@app.route("/delete/<id>",methods=["POST"])
@login_required
def delete(id):
    oid=safe_object_id(id)
    if not oid: flash("Invalid record ID.","danger"); return redirect(url_for("view"))
    try: result=expenses_collection.delete_one({"_id":oid,"user_id":session.get("user_id")}); flash("Record deleted successfully!" if result.deleted_count else "Record not found or access denied.","success" if result.deleted_count else "danger")
    except Exception: app.logger.exception("Record deletion error"); flash("Error deleting record.","danger")
    return redirect(url_for("view"))

@app.route("/edit/<id>",methods=["GET","POST"])
@login_required
def edit(id):
    oid=safe_object_id(id)
    if not oid: flash("Invalid record ID.","danger"); return redirect(url_for("view"))
    try: item=expenses_collection.find_one({"_id":oid,"user_id":session.get("user_id")})
    except Exception: item=None
    if not item: flash("Record not found or access denied.","danger"); return redirect(url_for("view"))
    if request.method=="POST":
        record_type=normalize_transaction_type(request.form.get("record_type"),normalize_transaction_type(item.get("type"),"expense"))
        try: amount=parse_amount(request.form.get("amount")); record_date=parse_record_date(request.form.get("date"))
        except ValueError as exc: flash(str(exc),"danger"); return redirect(url_for("edit",id=id))
        category=normalize_category(request.form.get("category"),"Income" if record_type=="income" else "Other"); party=normalize_text(request.form.get("party"),120); account=normalize_text(request.form.get("account"),80) or "Cash"; description=normalize_text(request.form.get("description"),500); reference=normalize_text(request.form.get("reference"),100)
        if record_type=="expense" and request.form.get("category")=="custom": category=normalize_category(request.form.get("custom_category"),"Other")
        if record_type in {"money_lent","money_returned","loan_received","loan_repayment"} and not party: flash("Person / Party is required for this transaction type.","danger"); return redirect(url_for("edit",id=id))
        try: expenses_collection.update_one({"_id":oid,"user_id":session.get("user_id")},{"$set":{"type":record_type,"amount":float(amount),"category":category,"date":record_date.isoformat(),"description":description,"party":party,"account":account,"reference":reference,"from_account":normalize_text(request.form.get("from_account"),80),"to_account":normalize_text(request.form.get("to_account"),80),"updated_at":utc_now()}}); flash("Record updated successfully!","success")
        except Exception: app.logger.exception("Record update error"); flash("Error updating record.","danger")
        return redirect(url_for("view"))
    return render_template("edit.html",item=record_to_view(item))

def summary_period_matches(trans_date,view_type,selected_date,from_date,to_date,today):
    if not trans_date:return False
    if view_type=="overall":return True
    if view_type=="weekly":return today-timedelta(days=6)<=trans_date<=today
    if view_type=="monthly":return trans_date.year==today.year and trans_date.month==today.month
    if view_type=="daily":return trans_date.isoformat()==selected_date
    if view_type=="range" and from_date and to_date:return from_date<=trans_date.isoformat()<=to_date
    return False

def summarize_items(items,view_type,selected_date,from_date,to_date,active_tab="all",selected_category=""):
    today=date.today(); filtered=[]; totals={"income":Decimal("0"),"expense":Decimal("0"),"money_lent":Decimal("0"),"money_returned":Decimal("0"),"loan_received":Decimal("0"),"loan_repayment":Decimal("0")}; category_totals={}
    for item in items:
        t=normalize_transaction_type(item.get("type")); category=normalize_category(item.get("category")); td=transaction_date(item)
        if active_tab in {"income","expense"} and t!=active_tab:continue
        if not summary_period_matches(td,view_type,selected_date,from_date,to_date,today):continue
        if selected_category and selected_category.lower()!="all" and category.lower()!=selected_category.lower():continue
        filtered.append(item); amount=money(item.get("amount")); totals[t]=totals.get(t,Decimal("0"))+amount
        category_totals.setdefault(category,{"income":Decimal("0"),"expense":Decimal("0")});
        if t in {"income","expense"}:category_totals[category][t]+=amount
    filtered=sort_by_added(filtered,True); totals["receivable"]=max(totals["money_lent"]-totals["money_returned"],Decimal("0")); totals["payable"]=max(totals["loan_received"]-totals["loan_repayment"],Decimal("0")); totals["net_income"]=totals["income"]-totals["expense"]; return filtered,totals,category_totals

@app.route("/summary")
@login_required
def summary():
    uid=session.get("user_id"); view_type=request.args.get("type","overall").lower(); view_type=view_type if view_type in {"overall","weekly","monthly","daily","range"} else "overall"; selected_date=request.args.get("date",date.today().isoformat()); selected_category=normalize_text(request.args.get("category"),80); active_tab=request.args.get("tab","all").lower(); active_tab=active_tab if active_tab in {"all","expense","income"} else "all"; from_date=request.args.get("from_date",""); to_date=request.args.get("to_date","")
    try: items=list(expenses_collection.find({"user_id":uid}))
    except Exception: app.logger.exception("Summary query error"); items=[]
    filtered,totals,category_totals=summarize_items(items,view_type,selected_date,from_date,to_date,active_tab,selected_category)
    return render_template("summary.html",expenses=[record_to_view(i) for i in filtered],total_income=float(totals["income"]),total_expense=float(totals["expense"]),total_savings=float(totals["net_income"]),total_balance=float(totals["net_income"]),money_lent=float(totals["money_lent"]),money_returned=float(totals["money_returned"]),receivable_outstanding=float(totals["receivable"]),loan_received=float(totals["loan_received"]),loan_repaid=float(totals["loan_repayment"]),payable_outstanding=float(totals["payable"]),category_totals={k:{"income":float(v["income"]),"expense":float(v["expense"])} for k,v in sorted(category_totals.items(),key=lambda p:p[1]["income"]+p[1]["expense"],reverse=True)},view_type=view_type,selected_date=selected_date,selected_category=selected_category,active_tab=active_tab,from_date=from_date,to_date=to_date)

@app.route("/summary/details")
@login_required
def summary_details():
    uid=session.get("user_id"); category=normalize_text(request.args.get("category"),80); view_type=request.args.get("type","overall").lower(); selected_date=request.args.get("date",date.today().isoformat()); from_date=request.args.get("from_date",""); to_date=request.args.get("to_date",""); view_type=view_type if view_type in {"overall","weekly","monthly","daily","range"} else "overall"
    try: items=list(expenses_collection.find({"user_id":uid}))
    except Exception: items=[]
    filtered,_,_=summarize_items(items,view_type,selected_date,from_date,to_date,"all",category)
    return render_template("summary_details.html",expenses=[record_to_view(i) for i in filtered],category=category,view_type=view_type,selected_date=selected_date,from_date=from_date,to_date=to_date)

@app.route("/summary/report")
@login_required
def download_report():
    uid=session.get("user_id"); view_type=request.args.get("type","overall").lower(); view_type=view_type if view_type in {"overall","weekly","monthly","daily","range"} else "overall"; selected_date=request.args.get("date",date.today().isoformat()); selected_category=normalize_text(request.args.get("category"),80); active_tab=request.args.get("tab","all").lower(); active_tab=active_tab if active_tab in {"all","expense","income"} else "all"; from_date=request.args.get("from_date",""); to_date=request.args.get("to_date","")
    try: items=list(expenses_collection.find({"user_id":uid}))
    except Exception: app.logger.exception("Report query error"); items=[]
    filtered,totals,category_totals=summarize_items(items,view_type,selected_date,from_date,to_date,active_tab,selected_category)
    total_income=totals["income"]; total_expense=totals["expense"]; net=totals["net_income"]
    buffer=io.BytesIO()
    try:
        doc=SimpleDocTemplate(buffer,pagesize=A4,topMargin=14*mm,bottomMargin=14*mm,leftMargin=14*mm,rightMargin=14*mm); styles=getSampleStyleSheet(); title_style=ParagraphStyle("StatementTitle",parent=styles["Title"],fontSize=19,leading=23,textColor=colors.HexColor("#0f172a"),spaceAfter=5); section_style=ParagraphStyle("Section",parent=styles["Heading3"],fontSize=11,leading=14,fontName="Helvetica-Bold",textColor=colors.HexColor("#0f172a"),spaceBefore=8,spaceAfter=5); meta_style=ParagraphStyle("StatementMeta",parent=styles["Normal"],fontSize=8.5,leading=12,textColor=colors.HexColor("#475569"),spaceAfter=10); cell_style=ParagraphStyle("StatementCell",parent=styles["Normal"],fontSize=7.3,leading=9,textColor=colors.HexColor("#0f172a")); header_style=ParagraphStyle("StatementHeader",parent=cell_style,fontName="Helvetica-Bold",textColor=colors.white); total_label_style=ParagraphStyle("TotalLabel",parent=styles["Normal"],fontSize=9,leading=12,fontName="Helvetica-Bold",textColor=colors.HexColor("#0f172a")); total_value_style=ParagraphStyle("TotalValue",parent=total_label_style,alignment=2)
        elements=[Paragraph("Expense Tracker — Accountant Financial Report",title_style)]; period=view_type.capitalize(); elements.append(Paragraph(f"<b>Prepared for:</b> {escape(normalize_text(session.get('first_name','User'),80))} &nbsp;&nbsp; <b>Period:</b> {escape(period)}<br/><b>Generated:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}",meta_style))
        summary_data=[[Paragraph("Actual Income",total_label_style),Paragraph(f"Rs {total_income:,.0f}",total_value_style)],[Paragraph("Actual Expenses",total_label_style),Paragraph(f"Rs {total_expense:,.0f}",total_value_style)],[Paragraph("Net Income",total_label_style),Paragraph(f"Rs {net:,.0f}",total_value_style)],[Paragraph("Money Given",total_label_style),Paragraph(f"Rs {totals['money_lent']:,.0f}",total_value_style)],[Paragraph("Money Received Back",total_label_style),Paragraph(f"Rs {totals['money_returned']:,.0f}",total_value_style)],[Paragraph("Outstanding Receivable",total_label_style),Paragraph(f"Rs {totals['receivable']:,.0f}",total_value_style)],[Paragraph("Loan Received",total_label_style),Paragraph(f"Rs {totals['loan_received']:,.0f}",total_value_style)],[Paragraph("Loan Outstanding",total_label_style),Paragraph(f"Rs {totals['payable']:,.0f}",total_value_style)]]; summary_table=Table(summary_data,colWidths=[110*mm,65*mm],hAlign="LEFT"); summary_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f8fafc")),("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#cbd5e1")),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8)])); elements.extend([summary_table,Spacer(1,10),Paragraph("Transaction Register",section_style)])
        table_data=[[Paragraph("#",header_style),Paragraph("Date",header_style),Paragraph("Type",header_style),Paragraph("Party",header_style),Paragraph("Category",header_style),Paragraph("Amount (Rs)",header_style)]]
        labels={"income":"Income","expense":"Expense","money_lent":"Money Given","money_returned":"Money Received Back","loan_received":"Loan Received","loan_repayment":"Loan Repayment","transfer_in":"Transfer In","transfer_out":"Transfer Out","adjustment":"Adjustment"}
        for idx,item in enumerate(filtered,1): table_data.append([Paragraph(str(idx),cell_style),Paragraph(escape(str(item.get("date","—"))),cell_style),Paragraph(escape(labels.get(normalize_transaction_type(item.get("type")),"Transaction")),cell_style),Paragraph(escape(normalize_text(item.get("party"),100) or "—"),cell_style),Paragraph(escape(normalize_category(item.get("category"))),cell_style),Paragraph(f"Rs {money(item.get('amount')):,.0f}",cell_style)])
        if len(table_data)==1: table_data.append([Paragraph("—",cell_style),Paragraph("—",cell_style),Paragraph("—",cell_style),Paragraph("—",cell_style),Paragraph("No transactions",cell_style),Paragraph("Rs 0",cell_style)])
        table=Table(table_data,colWidths=[18,58,75,75,100,76],repeatRows=1,hAlign="LEFT"); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f172a")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#cbd5e1")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)])); elements.extend([table,Spacer(1,12),Paragraph("Category Analysis",section_style)])
        category_rows=[[Paragraph("Category",header_style),Paragraph("Income (Rs)",header_style),Paragraph("Expense (Rs)",header_style),Paragraph("Net (Rs)",header_style)]]
        for category,v in sorted(category_totals.items(),key=lambda p:p[1]["income"]+p[1]["expense"],reverse=True): category_rows.append([Paragraph(escape(category),cell_style),Paragraph(f"{v['income']:,.0f}",cell_style),Paragraph(f"{v['expense']:,.0f}",cell_style),Paragraph(f"{v['income']-v['expense']:,.0f}",cell_style)])
        if len(category_rows)==1: category_rows.append([Paragraph("No category data",cell_style),Paragraph("0",cell_style),Paragraph("0",cell_style),Paragraph("0",cell_style)])
        category_table=Table(category_rows,colWidths=[88*mm,32*mm,32*mm,23*mm],repeatRows=1,hAlign="LEFT"); category_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#334155")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#cbd5e1")),("ALIGN",(1,1),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)])); elements.append(category_table); doc.build(elements)
    except Exception: app.logger.exception("PDF report generation error"); buffer.close(); flash("Unable to generate the PDF report. Please try again.","danger"); return redirect(url_for("summary"))
    buffer.seek(0); return send_file(buffer,mimetype="application/pdf",as_attachment=True,download_name=f"financial_report_{view_type}_{datetime.now().strftime('%Y%m%d')}.pdf")

@app.route("/sitemap.xml")
def sitemap(): return send_from_directory(app.root_path,"sitemap.xml")
@app.errorhandler(404)
def not_found(error): return render_template("404.html"),404
@app.errorhandler(500)
def server_error(error): app.logger.exception("Unhandled application error"); return render_template("500.html"),500
if __name__=="__main__": app.run(debug=True)
