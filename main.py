import json
import os
from datetime import datetime
from flask import Flask, render_template_string, request, flash, redirect, url_for, session
from app.crypto_engine import generate_key, encrypt_secret_answer, verify_student_claim

app = Flask(__name__)
import os

# Uses environment variables if set, otherwise falls back to defaults
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "ua_secret_session_key_2026")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "admin")


# 1. KEY GENERATION: Static symmetric key for the session
SYSTEM_KEY = generate_key()
DB_FILE = "database.json"

# Persistence helpers
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ------------------------------------------------------------------------------
# HTML TEMPLATES (Separated for Student vs Staff)
# ------------------------------------------------------------------------------

STUDENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UA Lost & Found Portal</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 30px; background-color: #f4f6f9; }
        .container { max-width: 600px; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin: auto; }
        h2 { color: #003366; margin-bottom: 5px; }
        p.subtitle { color: #555; font-size: 14px; margin-top: 0; }
        label { font-weight: bold; display: block; margin-top: 15px; }
        input, select { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { margin-top: 20px; width: 100%; padding: 12px; background: #003366; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; }
        button:hover { background: #002244; }
        .alert { padding: 12px; margin-bottom: 15px; border-radius: 4px; font-weight: bold; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-danger { background: #f8d7da; color: #721c24; }
        footer { margin-top: 30px; text-align: center; font-size: 12px; color: #aaa; }
        footer a { color: #aaa; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🏫 UA Campus Lost & Found</h2>
        <p class="subtitle">Student Item Claim Verification Portal</p>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        {% if not items %}
            <p>There are currently no unclaimed items logged in the system.</p>
        {% else %}
            <form action="/" method="POST">
                <label>Select Item to Claim:</label>
                <select name="selected_item" required>
                    {% for item_name, data in items.items() %}
                        <option value="{{ item_name }}">
                            {{ item_name }} (Found at {{ data['location'] }} — {{ data['timestamp'] }})
                        </option>
                    {% endfor %}
                </select>
                
                <label>Enter Secret Verification Proof:</label>
                <input type="text" name="user_attempt" placeholder="e.g., Specific sticker, engraver name, or mark" required>
                
                <button type="submit">Verify My Claim</button>
            </form>
        {% endif %}

        <footer>
            <p>© University of the Assumption — Information Assurance Project</p>
            <p><a href="/admin">Staff Access</a></p>
        </footer>
    </div>
</body>
</html>
"""

STAFF_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UA Staff Management Vault</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 30px; background-color: #2c3e50; }
        .container { max-width: 600px; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.3); margin: auto; }
        h2 { color: #2c3e50; margin-bottom: 5px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        label { font-weight: bold; display: block; margin-top: 15px; }
        input { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { margin-top: 20px; width: 100%; padding: 12px; background: #27ae60; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; font-weight: bold; }
        button:hover { background: #219150; }
        .alert { padding: 12px; margin-bottom: 15px; border-radius: 4px; font-weight: bold; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-danger { background: #f8d7da; color: #721c24; }
        .logout-btn { color: #e74c3c; text-decoration: none; font-weight: bold; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🔑 UA Staff Logging Portal</h2>
            {% if session.get('staff_logged_in') %}
                <a href="/logout" class="logout-btn">Logout</a>
            {% endif %}
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        {% if not session.get('staff_logged_in') %}
            <h3>Authorization Required</h3>
            <form action="/admin" method="POST">
                <label>Enter Staff Password:</label>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit" style="background:#2c3e50;">Authenticate</button>
            </form>
        {% else %}
            <h3>Register Found Item</h3>
            <form action="/admin/log" method="POST">
                <label>Item Name / Description:</label>
                <input type="text" name="item_name" placeholder="e.g., Black Asus Laptop" required>
                
                <label>Found Location:</label>
                <input type="text" name="location" placeholder="e.g., UA Library Room 201" required>
                
                <label>Secret Verification Proof (Encrypted):</label>
                <input type="password" name="secret_proof" placeholder="e.g., Frog sticker on back" required>
                
                <button type="submit">Encrypt & Save Item (AES-256)</button>
            </form>
            <p style="margin-top: 20px;"><a href="/" style="color: #2c3e50;">← Back to Student View</a></p>
        {% endif %}
    </div>
</body>
</html>
"""

# ------------------------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------------------------

# 1. PUBLIC STUDENT ROUTE (Default Root URL)
@app.route("/", methods=["GET", "POST"])
def student_view():
    db = load_db()
    if request.method == "POST":
        selected_item = request.form.get("selected_item")
        user_attempt = request.form.get("user_attempt", "").strip()

        if selected_item in db:
            record = db[selected_item]
            
            # Execute AES-256 Decryption & Verification
            is_valid, _ = verify_student_claim(
                user_input=user_attempt,
                ciphertext_b64=record["ciphertext"],
                iv_b64=record["iv"],
                key=SYSTEM_KEY
            )

            if is_valid:
                flash(f"✅ Claim Validated for '{selected_item}'! Please present this screen to UA Lost & Found staff.", "success")
            else:
                flash("❌ Verification Failed. Provided proof answer does not match the encrypted record.", "danger")

    return render_template_string(STUDENT_TEMPLATE, items=db)


# 2. PRIVATE STAFF AUTHENTICATION ROUTE
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == STAFF_PASSWORD:
            session["staff_logged_in"] = True
            flash("Staff authentication successful.", "success")
            return redirect(url_for("admin_login"))
        else:
            flash("Incorrect staff password!", "danger")
            
    return render_template_string(STAFF_TEMPLATE)


# 3. PRIVATE STAFF ITEM LOGGING ROUTE
@app.route("/admin/log", methods=["POST"])
def admin_log_item():
    if not session.get("staff_logged_in"):
        flash("Unauthorized access.", "danger")
        return redirect(url_for("admin_login"))

    db = load_db()
    item_name = request.form.get("item_name", "").strip()
    location = request.form.get("location", "").strip()
    secret_proof = request.form.get("secret_proof", "").strip()

    if item_name and secret_proof:
        ciphertext, iv = encrypt_secret_answer(secret_proof, SYSTEM_KEY)
        
        db[item_name] = {
            "location": location,
            "ciphertext": ciphertext,
            "iv": iv,
            "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M %p")
        }
        save_db(db)
        flash(f"Item '{item_name}' encrypted with AES-256 and saved to database!", "success")
    else:
        flash("Please fill in all required fields.", "danger")

    return redirect(url_for("admin_login"))


# 4. LOGOUT ROUTE
@app.route("/logout")
def logout():
    session.pop("staff_logged_in", None)
    flash("Logged out from staff portal.", "success")
    return redirect(url_for("student_view"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)