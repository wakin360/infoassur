import base64
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template_string, request, flash, redirect, url_for, session
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from app import database

# Initialize Flask App
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD")

# ==============================================================================
# CRYPTOGRAPHIC MODULE (AES-256)
# ==============================================================================

def generate_key() -> bytes:
    return os.urandom(32)

def encrypt_secret_answer(secret_text: str, key: bytes) -> tuple[str, str]:
    clean_bytes = secret_text.strip().lower().encode('utf-8')
    padded_bytes = pad(clean_bytes, AES.block_size)
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(padded_bytes)
    return base64.b64encode(ciphertext).decode('utf-8'), base64.b64encode(iv).decode('utf-8')

def decrypt_secret_answer(ciphertext_b64: str, iv_b64: str, key: bytes) -> str:
    ciphertext = base64.b64decode(ciphertext_b64)
    iv = base64.b64decode(iv_b64)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_padded = cipher.decrypt(ciphertext)
    return unpad(decrypted_padded, AES.block_size).decode('utf-8')

def verify_student_claim(user_input: str, ciphertext_b64: str, iv_b64: str, key: bytes) -> bool:
    try:
        decrypted_secret = decrypt_secret_answer(ciphertext_b64, iv_b64, key)
        return user_input.strip().lower() == decrypted_secret
    except Exception:
        return False

# The encryption key must remain stable across serverless invocations.
try:
    SYSTEM_KEY = bytes.fromhex(os.environ.get("ENCRYPTION_KEY", ""))
except ValueError:
    SYSTEM_KEY = b""

if len(SYSTEM_KEY) != 32:
    SYSTEM_KEY = b""

# ==============================================================================
# HTML TEMPLATES
# ==============================================================================

STUDENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UA Lost & Found Portal</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lora:wght@500;600;700&family=Source+Sans+3:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='portal.css') }}">
</head>
<body class="portal-body student-page">
    <div class="page-shell">
        <header class="masthead">
            <a class="brand" href="/">
                <img class="brand-seal" src="https://web.ua.edu.ph/wp-content/uploads/2024/09/ua-logo.png" alt="University of the Assumption seal">
                <span class="brand-name">University of the Assumption<span class="brand-unit">Campus Services</span></span>
            </a>
        </header>
        <main class="portal-main">
            <section class="hero-copy">
                <p class="eyebrow">Student services <span>/</span> Lost &amp; found</p>
                <h1>Lost something?<br><span>Let’s bring it home.</span></h1>
                <p class="hero-description">Browse recently found belongings and verify a claim with a detail only the owner would know.</p>
                <p class="campus-location">University of the Assumption<br>City of San Fernando, Pampanga</p>
            </section>
            <section class="container claim-panel">
                <p class="panel-kicker">Student claim portal</p>
                <h2>Find your item</h2>
                <p class="subtitle">Choose an item and enter its identifying detail.</p>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}" role="status">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        {% if storage_error %}
            <div class="alert alert-danger" role="alert">{{ storage_error }}</div>
        {% elif not items %}
            <div class="empty-state">
                <strong>No items are waiting to be claimed.</strong>
                <p>Check back later or contact the campus staff desk.</p>
            </div>
        {% else %}
            <form action="/" method="POST">
                <label for="selected-item">Select an item</label>
                <select id="selected-item" name="selected_item" required>
                    {% for item_name, data in items.items() %}
                        <option value="{{ item_name }}">
                            {{ item_name }} (Found at {{ data['location'] }} — {{ data['timestamp'] }})
                        </option>
                    {% endfor %}
                </select>
                
                <label for="user-attempt">Identifying detail</label>
                <input id="user-attempt" type="text" name="user_attempt" placeholder="A sticker, engraving, or distinct mark" required>
                
                <button type="submit">Verify claim</button>
            </form>
        {% endif %}

            </section>
        </main>
        <footer class="site-footer"><span>University of the Assumption</span><span>Information Assurance Project</span></footer>
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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lora:wght@500;600;700&family=Source+Sans+3:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='portal.css') }}">
</head>
<body class="portal-body staff-page">
    <div class="page-shell">
        <header class="masthead">
            <a class="brand" href="/">
                <img class="brand-seal" src="https://web.ua.edu.ph/wp-content/uploads/2024/09/ua-logo.png" alt="University of the Assumption seal">
                <span class="brand-name">University of the Assumption<span class="brand-unit">Campus Services</span></span>
            </a>
            {% if session.get('staff_logged_in') %}
                <a href="/logout" class="masthead-link">Log out</a>
            {% else %}
                <a href="/" class="masthead-link">Student portal</a>
            {% endif %}
        </header>
        <main class="portal-main">
            <section class="hero-copy">
                <p class="eyebrow">Campus services <span>/</span> Staff</p>
                <h1>Care for what’s<br><span>found on campus.</span></h1>
                <p class="hero-description">Record found belongings securely so students can identify and reclaim what belongs to them.</p>
                <p class="campus-location">University of the Assumption<br>City of San Fernando, Pampanga</p>
            </section>
            <section class="container staff-panel">
                <p class="panel-kicker">Staff workspace</p>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}" role="status">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        {% if not session.get('staff_logged_in') %}
            {% if setup_error %}
                <div class="alert alert-danger" role="alert">{{ setup_error }}</div>
            {% else %}
                <h2>Staff sign in</h2>
                <p class="subtitle">Authorized staff can register found belongings here.</p>
                <form action="/admin" method="POST">
                    <label for="staff-password">Staff password</label>
                    <input id="staff-password" type="password" name="password" placeholder="Enter password" required>
                    <button type="submit">Sign in</button>
                </form>
            {% endif %}
        {% else %}
            <h2>Register an item</h2>
            <p class="subtitle">Keep one identifying detail private for claim verification.</p>
            <form action="/admin/log" method="POST">
                <label for="item-name">Item name or description</label>
                <input id="item-name" type="text" name="item_name" placeholder="Black laptop" required>
                
                <label for="item-location">Where it was found</label>
                <input id="item-location" type="text" name="location" placeholder="Library, second floor" required>
                
                <label for="secret-proof">Private identifying detail</label>
                <input id="secret-proof" type="password" name="secret_proof" placeholder="A sticker, engraving, or distinct mark" required>
                
                <button type="submit">Encrypt and save item</button>
            </form>
            <p class="panel-return"><a href="/">Return to student portal</a></p>
        {% endif %}
            </section>
        </main>
        <footer class="site-footer"><span>University of the Assumption</span><span>Staff access</span></footer>
    </div>
</body>
</html>
"""

# ==============================================================================
# FLASK ROUTES
# ==============================================================================

@app.route("/", methods=["GET", "POST"])
def student_view():
    storage_error = None
    if len(SYSTEM_KEY) != 32:
        items = {}
        storage_error = "Item verification is not configured. Please contact campus staff."
    else:
        try:
            items = database.load_items()
        except (database.StorageNotConfigured, RuntimeError):
            items = {}
            storage_error = "Shared item storage is not configured or is temporarily unavailable. Please contact campus staff."

    if request.method == "POST":
        selected_item = request.form.get("selected_item")
        user_attempt = request.form.get("user_attempt", "").strip()

        if selected_item in items:
            record = items[selected_item]
            is_valid = verify_student_claim(
                user_input=user_attempt,
                ciphertext_b64=record["ciphertext"],
                iv_b64=record["iv"],
                key=SYSTEM_KEY
            )

            if is_valid:
                flash(f"Claim validated for '{selected_item}'. Please present this screen to campus staff.", "success")
            else:
                flash("Verification failed. The identifying detail does not match the record.", "danger")

    return render_template_string(STUDENT_TEMPLATE, items=items, storage_error=storage_error)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if not STAFF_PASSWORD or not app.secret_key or not database.is_configured() or len(SYSTEM_KEY) != 32:
            return render_template_string(
                STAFF_TEMPLATE,
                setup_error="Staff access is not configured. Contact the system administrator.",
            )

        if request.form.get("password") == STAFF_PASSWORD:
            session["staff_logged_in"] = True
            flash("Staff authentication successful.", "success")
            return redirect(url_for("admin_login"))
        else:
            flash("Incorrect staff password!", "danger")
            
    setup_error = None
    if not STAFF_PASSWORD or not app.secret_key or not database.is_configured() or len(SYSTEM_KEY) != 32:
        setup_error = "Staff access and shared storage are not fully configured. Contact the system administrator."
    return render_template_string(STAFF_TEMPLATE, setup_error=setup_error)


@app.route("/admin/log", methods=["POST"])
def admin_log_item():
    if not session.get("staff_logged_in"):
        flash("Unauthorized access.", "danger")
        return redirect(url_for("admin_login"))

    if not database.is_configured() or len(SYSTEM_KEY) != 32:
        flash("Shared storage is not configured. The item was not saved.", "danger")
        return redirect(url_for("admin_login"))

    item_name = request.form.get("item_name", "").strip()
    location = request.form.get("location", "").strip()
    secret_proof = request.form.get("secret_proof", "").strip()

    if item_name and secret_proof:
        try:
            ciphertext, iv = encrypt_secret_answer(secret_proof, SYSTEM_KEY)
            database.save_item(item_name, {
                "location": location,
                "ciphertext": ciphertext,
                "iv": iv,
                "timestamp": datetime.now(ZoneInfo("Asia/Manila")).strftime("%Y-%m-%d %I:%M %p"),
            })
            flash(f"Item '{item_name}' encrypted with AES-256 and saved!", "success")
        except RuntimeError:
            flash("Could not save the item to shared storage. Please try again.", "danger")
    else:
        flash("Please fill in all required fields.", "danger")

    return redirect(url_for("admin_login"))


@app.route("/logout")
def logout():
    session.pop("staff_logged_in", None)
    flash("Logged out from staff portal.", "success")
    return redirect(url_for("student_view"))


app = app

if __name__ == "__main__":
    app.run(debug=True, port=5000)