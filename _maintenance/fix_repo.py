from pathlib import Path
p=Path('app.py')
s=p.read_text()
s=s.replace('app.secret_key = "expense_secret_key"','app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")')
s=s.replace('from datetime import datetime, timedelta','from datetime import datetime, timedelta, timezone')
needle='def login_required(f):\n'
helpers='''def utc_now():\n    return datetime.now(timezone.utc)\n\ndef parse_amount(value):\n    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP\n    try:\n        amount = Decimal(str(value).strip().replace(",", "")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)\n        if not amount.is_finite() or amount <= 0:\n            raise ValueError\n        return float(amount)\n    except (InvalidOperation, ValueError, TypeError):\n        raise ValueError("Amount must be a positive valid number.")\n\ndef parse_record_date(value):\n    if not value:\n        raise ValueError("Date is required.")\n    try:\n        return datetime.strptime(value, "%Y-%m-%d").date()\n    except (TypeError, ValueError):\n        raise ValueError("Please enter a valid date.")\n\ndef record_created_at(record):\n    value = record.get("created_at")\n    if isinstance(value, datetime):\n        return value\n    if isinstance(value, str):\n        try:\n            return datetime.fromisoformat(value.replace("Z", "+00:00"))\n        except ValueError:\n            pass\n    oid = record.get("_id")\n    if isinstance(oid, ObjectId):\n        return oid.generation_time\n    return datetime.min.replace(tzinfo=timezone.utc)\n\ndef sort_by_added(records, newest_first=True):\n    return sorted(records, key=record_created_at, reverse=newest_first)\n\n'''
s=s.replace(needle,helpers+needle)
old='''                expenses_collection.insert_one({\n                    "user_id": uid,\n                    "type": "income",\n                    "amount": float(amount) if amount else 0.0,'''
new='''                amount_value = parse_amount(amount)\n                date_value = parse_record_date(date)\n                expenses_collection.insert_one({\n                    "user_id": uid,\n                    "type": "income",\n                    "amount": amount_value,'''
s=s.replace(old,new)
s=s.replace('''                    "date": date,\n                    "description": description\n                })''','''                    "date": date_value.strftime("%Y-%m-%d"),\n                    "description": description,\n                    "created_at": utc_now().isoformat()\n                })''',1)
old='''                expenses_collection.insert_one({\n                    "user_id": uid,\n                    "type": "expense",\n                    "amount": float(amount) if amount else 0.0,'''
new='''                amount_value = parse_amount(amount)\n                date_value = parse_record_date(date)\n                expenses_collection.insert_one({\n                    "user_id": uid,\n                    "type": "expense",\n                    "amount": amount_value,'''
s=s.replace(old,new)
idx=s.find('''                expenses_collection.insert_one({\n                    "user_id": uid,\n                    "type": "expense",''')
if idx!=-1:
    tail=s[idx:]
    tail=tail.replace('''                    "date": date,\n                    "description": description\n                })''','''                    "date": date_value.strftime("%Y-%m-%d"),\n                    "description": description,\n                    "created_at": utc_now().isoformat()\n                })''',1)
    s=s[:idx]+tail
s=s.replace('''    try:\n        latest_expense = expenses_collection.find_one(\n            {"user_id": uid, "type": "expense"}, sort=[("_id", -1)]\n        )\n    except Exception:\n        latest_expense = None\n    last_used_category = latest_expense.get("category", "") if latest_expense else ""''','''    try:\n        recent_expenses = sort_by_added(list(expenses_collection.find({"user_id": uid, "type": "expense"})))\n        latest_expense = recent_expenses[0] if recent_expenses else None\n    except Exception:\n        latest_expense = None\n    last_used_category = latest_expense.get("category", "") if latest_expense else ""''')
s=s.replace('''        expenses = list(expenses_collection.find(query).sort("date", -1))''','''        expenses = sort_by_added(list(expenses_collection.find(query)), newest_first=True)''')
s=s.replace('''        expenses_collection.delete_one({"_id": ObjectId(id)})''','''        expenses_collection.delete_one({"_id": ObjectId(id), "user_id": session.get("user_id")})''')
s=s.replace('''        expense = expenses_collection.find_one({"_id": oid})''','''        expense = expenses_collection.find_one({"_id": oid, "user_id": session.get("user_id")})''')
s=s.replace('''            expenses_collection.update_one({"_id": oid}, {"$set": {\n                "type": trans_type,\n                "amount": float(request.form.get("amount", 0)),\n                "category": request.form.get("category", "Other"),\n                "date": request.form.get("date"),\n                "description": request.form.get("description", "")\n            }})''','''            amount_value = parse_amount(request.form.get("amount", 0))\n            date_value = parse_record_date(request.form.get("date"))\n            expenses_collection.update_one({"_id": oid, "user_id": session.get("user_id")}, {"$set": {\n                "type": trans_type,\n                "amount": amount_value,\n                "category": request.form.get("category", "Other"),\n                "date": date_value.strftime("%Y-%m-%d"),\n                "description": request.form.get("description", ""),\n                "updated_at": utc_now().isoformat()\n            }})''')
start=s.find('@app.route("/biometric_login", methods=["POST"])')
if start!=-1:
    end=s.find('@app.route("/signup"', start)
    block='''@app.route("/biometric_login", methods=["POST"])\ndef biometric_login():\n    return {"status": "error", "message": "Biometric login is not configured securely yet."}, 501\n\n'''
    s=s[:start]+block+s[end:]
# Clean tracked Python cache and strengthen ignore rules.
Path('app.py').write_text(s)
gitignore=Path('.gitignore')
existing=gitignore.read_text() if gitignore.exists() else ''
for entry in ['__pycache__/','*.py[cod]','users.json']:
    if entry not in existing.splitlines(): existing += ('\n' if existing and not existing.endswith('\n') else '') + entry + '\n'
gitignore.write_text(existing)
cache=Path('__pycache__')
if cache.exists():
    import shutil
    shutil.rmtree(cache)
