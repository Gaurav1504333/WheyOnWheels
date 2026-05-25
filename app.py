from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import mysql.connector
from datetime import datetime
import traceback
import os

app = Flask(__name__)
app.secret_key = 'b1e2c3d4a5f67890123456789abcdef'

@app.route("/__ping")
def ping():
    return "APP IS RUNNING"

from flask import send_from_directory
import os

@app.route("/sitemap.xml", strict_slashes=False)
def sitemap():
    return send_from_directory(
        app.root_path,
        "sitemap.xml",
        mimetype="application/xml"
    )

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT", 3306)),
            autocommit=True
        )
    except mysql.connector.Error as e:
        print("DB Connection Error:", e)
        return None


@app.route("/db-test")
def db_test():
    conn = get_db_connection()
    if conn:
        return "Database connected successfully!"
    else:
        return "Database connection failed!"


# Google Sheet CSV export URLs
Smoothie_MENU_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSob3Z4VWarQN4fiwdWX3UjH35ZsGddD5oGQXvd0FVqkg-NQw9GkCzLeXyVQeakmLzeZvIfXYace_3C/pub?output=csv"
Toast_MENU_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSg9CzlFJnSNaL_VTcI0X7D5w_tbsc6Yr0dyrTH9-8Sj_-xaU13gFEnUygd1v4GKwQWvu-iaqFdzwRb/pub?output=csv"
Workout_MENU_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRo6yrMCi9ZemNFmd_P91rTd5jp2VBWPE1xi-HMWk6hMo1eQGD_6NIfOaxew5wXZaNNZMqITLmbflmK/pub?output=csv"
ICECREAM_MENU_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTGMpB5gjOd0uMLhYUSuvW-tsav2YHEtqwDVGBiVME6rdoZJbwCwFkcueaWsbf1NUUo6Lzg00fjqh6z/pub?output=csv"
REFERRAL_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSMJKLe-A2NZASP1sl1dNKRdK5Ne-3h-4Cy3bI4I0N_Ikh-j5Tk1bLFqO9DXgO88u3i87REtZJDZWEk/pub?output=csv"

# Make 'user' globally available in templates
@app.context_processor
def inject_user():
    return dict(user=session.get('user'))


def validate_referral_code(code):
    """Returns (is_valid: bool) by checking the referral Google Sheet."""
    try:
        import requests as req
        res = req.get(REFERRAL_SHEET_URL, timeout=6)
        valid_codes = [
            row.split(",")[0].strip().lower()
            for row in res.text.split("\n")
            if row.strip()
        ]
        return code.strip().lower() in valid_codes
    except Exception as e:
        print("❌ Referral sheet error:", e)
        return False


@app.route('/')
def home():
    db = get_db_connection()
    if not db:
        print("❌ Database temporarily unavailable")
        return render_template('index.html', reviews=[])

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM reviews ORDER BY created_at DESC")
        reviews = cursor.fetchall()
        cursor.close()
        db.close()
    except Exception as e:
        print("❌ Error fetching reviews:", e)
        reviews = []

    return render_template('index.html', reviews=reviews)


@app.route('/menu_select')
def menu_select():
    return render_template('menu_select.html')

@app.route('/menu_toasts')
def menu_toasts():
    try:
        df = pd.read_csv(Toast_MENU_CSV_URL)
        df.fillna('', inplace=True)
        items = df.to_dict(orient='records')
    except Exception as e:
        print("Error loading Google Sheet:", e)
        items = []
    return render_template('menu.html', menu_items=items)

@app.route('/menu_workout')
def menu_workout():
    try:
        df = pd.read_csv(Workout_MENU_CSV_URL)
        df.fillna('', inplace=True)
        items = df.to_dict(orient='records')
    except Exception as e:
        print("Error loading Google Sheet:", e)
        items = []
    return render_template('menu.html', menu_items=items)

@app.route('/menu_smoothies')
def menu_smoothie():
    try:
        df = pd.read_csv(Smoothie_MENU_CSV_URL)
        df.fillna('', inplace=True)
        items = df.to_dict(orient='records')
    except Exception as e:
        print("Error loading Google Sheet:", e)
        items = []
    return render_template('menu.html', menu_items=items)

@app.route('/menu_icecream')
def menu_icecream():
    try:
        df = pd.read_csv(ICECREAM_MENU_CSV_URL)
        df.fillna('', inplace=True)
        items = df.to_dict(orient='records')
    except Exception as e:
        print("Error loading Icecream Google Sheet:", e)
        items = []
    return render_template('menu.html', menu_items=items)


from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
from datetime import datetime
import traceback

@app.route('/order_select')
def order_select():
    return render_template('order_select.html')


@app.route('/order_smoothie', methods=['GET', 'POST'])
def order_smoothie():
    if 'user' not in session:
        return redirect('/login')

    try:
        df = pd.read_csv(Smoothie_MENU_CSV_URL)
        df.fillna('', inplace=True)
        smoothies = df.iloc[0:21, 1].dropna().tolist()
        addons = df.iloc[21:29, 1].dropna().tolist()
        prices = df.set_index(df.columns[1])[df.columns[4]].to_dict()
    except Exception as e:
        print("❌ Dropdown load error:", e)
        smoothies, addons, prices = [], [], {}

    if request.method == 'POST':
        smoothie_list = request.form.getlist('smoothie[]')
        quantity_list = request.form.getlist('quantity[]')

        # Robust addon collection
        addon_list = []
        for key in request.form.keys():
            if key.startswith('addon'):
                addon_list.extend([v for v in request.form.getlist(key) if v and v.strip()])
        if not addon_list:
            addon_list = [a for a in request.form.getlist('addon[]') if a and a.strip()]

        # Referral code
        referral_code = request.form.get('referral_code', '').strip().lower()
        referral_valid = False
        referral_discount = 0

        if referral_code:
            referral_valid = validate_referral_code(referral_code)
            if referral_valid:
                referral_discount = 10  # ₹10 flat discount for smoothies

        # Build order string
        smoothie_data = [
            f"{s.strip()} x{q.strip()}"
            for s, q in zip(smoothie_list, quantity_list)
            if s and s.strip() and q and q.strip().isdigit()
        ]
        smoothie_str = ', '.join(smoothie_data)
        addon_str = ', '.join([a.strip() for a in addon_list if a and a.strip()])

        if not smoothie_str and not addon_str:
            flash("Please select at least one smoothie or addon.", "error")
            return redirect('/order_smoothie')

        # Calculate total (no multi-item discount)
        total_bill = 0.0

        for s, q in zip(smoothie_list, quantity_list):
            if s and s.strip() and q and q.strip().isdigit():
                price = float(prices.get(s.strip(), 0) or 0)
                qty = int(q.strip())
                total_bill += price * qty

        for a in addon_list:
            if a and a.strip():
                total_bill += float(prices.get(a.strip(), 0) or 0)

        # Referral discount
        if referral_valid:
            total_bill = max(total_bill - referral_discount, 0)

        total_bill = round(total_bill, 2)

        session['pending_order'] = {
            'type': 'normal',
            'category': 'smoothie',
            'smoothie': smoothie_str,
            'addons': addon_str,
            'quantity': ','.join(quantity_list),
            'total_bill': total_bill,
            'smoothie_price': total_bill,
            'referral_code': referral_code if referral_valid else '',
            'referral_discount': referral_discount if referral_valid else 0
        }

        if referral_valid:
            flash(f"✅ Referral code applied! ₹10 discount added.", "success")

        flash(f"Smoothie order added. Total: ₹{total_bill}", "info")
        return redirect('/payment_page')

    return render_template(
        'order_smoothie.html',
        smoothies=smoothies,
        addons=addons,
        prices=prices
    )


@app.route('/order_toast', methods=['GET', 'POST'])
def order_toast():
    if 'user' not in session:
        return redirect('/login')

    try:
        df = pd.read_csv(Toast_MENU_CSV_URL)
        df.fillna('', inplace=True)

        toasts = df.iloc[0:15, 1].dropna().tolist()

        price_col = df.columns[4]
        df[price_col] = (
            df[price_col]
            .astype(str)
            .str.replace("₹", "", regex=False)
            .str.strip()
        )
        df[price_col] = pd.to_numeric(df[price_col], errors="coerce").fillna(0)

        prices_backend = {
            str(name).strip().lower(): float(price)
            for name, price in zip(df.iloc[:, 1], df[price_col])
        }
        prices_frontend = {
            str(name): float(price)
            for name, price in zip(df.iloc[:, 1], df[price_col])
        }

    except Exception as e:
        print("❌ Toast dropdown load error:", str(e))
        flash("Unable to load toast menu. Please try again.", "error")
        toasts, prices_backend, prices_frontend = [], {}, {}

    if request.method == 'POST':
        toast_list = request.form.getlist('toast[]')
        quantity_list = request.form.getlist('quantity[]')

        # Referral code
        referral_code = request.form.get('referral_code', '').strip().lower()
        referral_valid = False
        referral_discount = 0

        if referral_code:
            referral_valid = validate_referral_code(referral_code)

        toast_data = [
            f"{t.strip()} x{q.strip()}"
            for t, q in zip(toast_list, quantity_list)
            if t and t.strip() and q and q.strip().isdigit()
        ]
        toast_str = ', '.join(toast_data)

        if not toast_str:
            flash("Please select at least one toast item.", "error")
            return redirect('/order_toast')

        # Calculate total (no multi-item discount)
        total_bill = 0.0

        for t, q in zip(toast_list, quantity_list):
            if t and t.strip() and q and q.strip().isdigit():
                qty = int(q.strip())
                key = t.strip().lower()
                price = prices_backend.get(key, 0)
                total_bill += price * qty

        # Referral discount (10%)
        if referral_valid:
            referral_discount = round(total_bill * 0.10, 2)
            total_bill = round(max(total_bill - referral_discount, 0), 2)

        total_bill = round(total_bill, 2)

        if referral_valid:
            flash(f"✅ Referral code applied! ₹{referral_discount} discount added.", "success")

        session['pending_order'] = {
            'type': 'normal',
            'category': 'toast',
            'toast': toast_str,
            'smoothie': '',
            'addons': '',
            'combo': '',
            'quantity': ','.join(quantity_list),
            'total_bill': total_bill,
            'referral_code': referral_code if referral_valid else '',
            'referral_discount': referral_discount
        }

        flash(f"Toast order added. Total: ₹{total_bill}", "info")
        return redirect('/payment_page')

    return render_template(
        'order_toast.html',
        toasts=toasts,
        prices=prices_frontend
    )


from itertools import zip_longest

@app.route('/order_workout', methods=['GET', 'POST'])
def order_workout():
    if 'user' not in session:
        return redirect('/login')

    try:
        df = pd.read_csv(Workout_MENU_CSV_URL)
        df.fillna('', inplace=True)

        workouts = df.iloc[0:11, 1].dropna().tolist()
        addons = df.iloc[11:15, 1].dropna().tolist()
        combos = df.iloc[15:20, 1].dropna().tolist()

        prices = df.set_index(df.columns[1])[df.columns[-1]].to_dict()

    except Exception as e:
        print("❌ Workout dropdown load error:", e)
        workouts, addons, combos, prices = [], [], [], {}

    if request.method == 'POST':
        workout_list = request.form.getlist('workout[]')
        quantity_list = request.form.getlist('quantity[]')
        addon_list = request.form.getlist('addon[]')

        combo = request.form.get('combo', '').strip()
        combo_addon = request.form.get('combo_addon', '').strip()

        try:
            combo_qty = int(request.form.get('combo_quantity', 1))
        except:
            combo_qty = 1

        # Calculate total (no multi-item discount)
        total_bill = 0.0
        workout_display = []

        max_len = max(len(workout_list), len(quantity_list), len(addon_list))

        for i in range(max_len):
            w = workout_list[i].strip() if i < len(workout_list) else ''
            q_raw = quantity_list[i].strip() if i < len(quantity_list) else ''
            a = addon_list[i].strip() if i < len(addon_list) else ''

            if not w:
                continue

            try:
                qty = int(q_raw) if q_raw.isdigit() else 1
            except:
                qty = 1

            price = float(prices.get(w, 0))
            total_bill += price * qty
            workout_display.append(f"{w} x{qty}")

            if a:
                addon_price = float(prices.get(a, 0))
                total_bill += addon_price * qty

        if combo:
            total_bill += float(prices.get(combo, 0)) * max(combo_qty, 1)

        if combo_addon:
            total_bill += float(prices.get(combo_addon, 0)) * max(combo_qty, 1)

        total_bill = round(total_bill, 2)

        session['pending_order'] = {
            'type': 'normal',
            'category': 'workout',
            'workout': ", ".join(workout_display),
            'addons': ", ".join([x for x in addon_list if x.strip()]),
            'combo': combo,
            'combo_addon': combo_addon,
            'combo_qty': combo_qty,
            'quantity_list': quantity_list,
            'total_bill': total_bill,
        }

        return redirect('/payment_page')

    return render_template(
        'order_workout.html',
        workouts=workouts,
        addons=addons,
        combos=combos,
        prices=prices
    )


@app.route('/order_icecream', methods=['GET', 'POST'])
def order_icecream():
    if 'user' not in session:
        return redirect('/login')

    try:
        df = pd.read_csv(ICECREAM_MENU_CSV_URL)
        df.fillna('', inplace=True)

        icecreams = df["Item Name"].dropna().tolist()

        df["Price (₹)"] = (
            df["Price (₹)"]
            .astype(str)
            .str.replace("₹", "")
            .str.strip()
        )
        df["Price (₹)"] = pd.to_numeric(df["Price (₹)"], errors="coerce")
        prices = df.set_index("Item Name")["Price (₹)"].to_dict()

    except Exception as e:
        print("❌ Icecream dropdown load error:", str(e))
        flash("Unable to load icecream menu. Please try again.", "error")
        icecreams, prices = [], {}

    if request.method == 'POST':
        icecream_list = request.form.getlist('icecream[]')
        quantity_list = request.form.getlist('quantity[]')

        # Referral code
        referral_code = request.form.get('referral_code', '').strip().lower()
        referral_valid = False
        referral_discount = 0

        if referral_code:
            referral_valid = validate_referral_code(referral_code)

        icecream_data = [
            f"{item} x{qty}"
            for item, qty in zip(icecream_list, quantity_list)
            if item and qty.isdigit()
        ]
        icecream_str = ", ".join(icecream_data)

        if not icecream_str:
            flash("Please select at least one icecream item.", "error")
            return redirect('/order_icecream')

        total_bill = 0
        for item, qty in zip(icecream_list, quantity_list):
            if item and qty.isdigit():
                qty = int(qty)
                price = float(prices.get(item, 0))
                total_bill += price * qty

        # Referral discount (10%)
        if referral_valid:
            referral_discount = round(total_bill * 0.10, 2)
            total_bill = round(max(total_bill - referral_discount, 0), 2)

        total_bill = round(total_bill, 2)

        if referral_valid:
            flash(f"✅ Referral code applied! ₹{referral_discount} discount added.", "success")

        session['pending_order'] = {
            'type': 'normal',
            'category': 'icecream',
            'smoothie': '',
            'toast': '',
            'workout': '',
            'icecream': icecream_str,
            'quantity': ','.join(quantity_list),
            'addons': '',
            'combo': '',
            'total_bill': total_bill,
            'referral_code': referral_code if referral_valid else '',
            'referral_discount': referral_discount
        }

        return redirect('/payment_page')

    return render_template(
        'order_icecream.html',
        icecreams=icecreams,
        prices=prices
    )


@app.route('/payment_page', methods=['GET', 'POST'])
def payment_page():
    if 'user' not in session:
        return redirect('/login')

    pending_order = session.get('pending_order')
    if not pending_order:
        flash("No order selected.", "error")
        return redirect('/orderselect')

    user_id = session['user']['user_id']

    db = get_db_connection()
    if not db:
        flash("Database temporarily unavailable.", "error")
        return redirect('/')

    try:
        cursor = db.cursor(dictionary=True)

        # Operators
        import requests, csv, io
        SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQrzOKK1RFl-aMdq36fi6W79p1YUgMbKYqShXQCitS7klGY_24KBeTHTsoAPsCjs_zzFEF2l8AjebhN/pub?output=csv"
        operator_data = {}

        try:
            response = requests.get(SHEET_URL, timeout=6)
            csv_data = list(csv.reader(io.StringIO(response.text)))
            for row in csv_data[1:]:
                if len(row) >= 3:
                    operator_data[row[1].strip()] = {
                        "name": row[0].strip(),
                        "location": row[2].strip()
                    }
        except:
            pass

        valid_code_entered = session.get("valid_code_entered", False)
        operator_code = session.get("operator_code", "")
        operator_name = session.get("operator_name", "")
        operator_location = session.get("operator_location", "")

        def safe_float(v, f=0.0):
            try: return float(v)
            except: return f

        total_bill = safe_float(pending_order.get("total_bill"))
        referral_discount = safe_float(pending_order.get("referral_discount", 0))

        # POST
        if request.method == "POST":
            operator_code_form = request.form.get("operator_code", "").strip()
            payment_mode = request.form.get("payment_mode", "").upper()

            if operator_code_form and not payment_mode:
                if operator_code_form in operator_data:
                    session["valid_code_entered"] = True
                    session["operator_code"] = operator_code_form
                    session["operator_name"] = operator_data[operator_code_form]["name"]
                    session["operator_location"] = operator_data[operator_code_form]["location"]
                    flash(f"Operator verified: {operator_data[operator_code_form]['name']}", "success")
                else:
                    flash("Invalid operator code.", "error")
                return redirect("/payment_page")

            if not payment_mode:
                flash("Please select a payment mode.", "error")
                return redirect("/payment_page")

            if operator_code_form and operator_code_form in operator_data:
                oc = operator_code_form
                on = operator_data[operator_code_form]["name"]
                ol = operator_data[operator_code_form]["location"]
            elif valid_code_entered:
                oc = operator_code
                on = operator_name
                ol = operator_location
            else:
                oc = on = ol = None

            qty_raw = pending_order.get("quantity_list") or pending_order.get("quantity") or "1"
            quantity_clean = ",".join(qty_raw) if isinstance(qty_raw, list) else str(qty_raw)

            # Insert order — reward_points_used and reward_points_earned always 0
            cursor.execute("""
                INSERT INTO orders (
                    user_id, name, contact,
                    smoothie, toast, icecream, workout,
                    quantity, addons, combo,
                    order_time, total_bill,
                    reward_points_used, reward_points_earned,
                    payment_mode
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        NOW(),%s,%s,%s,%s)
            """, (
                user_id,
                session['user']['username'],
                session['user']['phone'],
                pending_order.get("smoothie", ""),
                pending_order.get("toast", ""),
                pending_order.get("icecream", ""),
                pending_order.get("workout", ""),
                quantity_clean,
                pending_order.get("addons", ""),
                pending_order.get("combo", ""),
                total_bill,
                0,   # reward_points_used — always 0
                0,   # reward_points_earned — always 0
                payment_mode
            ))

            order_id = cursor.lastrowid

            if oc:
                cursor.execute("""
                    INSERT INTO operator_orders (
                        operator_name, operator_code, operator_location,
                        order_id, user_id, total_amount,
                        payment_mode, order_type
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    on, oc, ol,
                    order_id, user_id,
                    total_bill,
                    payment_mode,
                    pending_order.get("type", "normal")
                ))

            db.commit()

            for k in ["pending_order", "valid_code_entered",
                      "operator_code", "operator_name", "operator_location"]:
                session.pop(k, None)

            flash(f"Payment successful! Paid ₹{total_bill}", "success")
            return redirect("/profile")

        # GET
        return render_template(
            "payment_page.html",
            order=pending_order,
            valid_code_entered=valid_code_entered,
            operator_name=operator_name,
            operator_code=operator_code,
            operator_location=operator_location,
            total_bill=total_bill,
            referral_discount=referral_discount
        )

    finally:
        cursor.close()
        db.close()


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        birthday = request.form.get('birthday')
        gender = request.form.get('gender')
        goal = request.form.get('goal')

        if not email or '@' not in email:
            flash("Please enter a valid email.", "error")
            return redirect('/signup')

        if not phone.isdigit() or len(phone) != 10:
            flash("Please enter a valid 10-digit phone number.", "error")
            return redirect('/signup')

        if not birthday:
            flash("Please select your birthday.", "error")
            return redirect('/signup')

        if not gender:
            flash("Please select your gender.", "error")
            return redirect('/signup')

        if not goal:
            flash("Please select your fitness goal.", "error")
            return redirect('/signup')

        db = get_db_connection()
        if not db:
            flash("Database temporarily unavailable.", "error")
            return redirect('/signup')

        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("""
                INSERT INTO users (username, email, phone, birthday, gender, goal)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, email, phone, birthday, gender, goal))
            db.commit()
            flash("Signup successful. Please log in.", "success")
            return redirect('/login')

        except mysql.connector.IntegrityError:
            flash("Email already exists. Please try logging in.", "error")
            return redirect('/signup')

        finally:
            cursor.close()
            db.close()

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')

        db = get_db_connection()
        if not db:
            flash("Database temporarily unavailable.", "error")
            return redirect('/login')

        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
            user = cursor.fetchone()

            if user:
                session['user'] = {
                    'username': user['username'],
                    'email': user['email'],
                    'phone': user['phone'],
                    'user_id': user['user_id']
                }
                flash(f"Welcome, {user['username']}!", "success")
                return redirect('/')
            else:
                flash("Phone number not found. Please sign up.", "error")
                return redirect('/login')

        finally:
            cursor.close()
            db.close()

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


from datetime import datetime
import traceback
from flask import render_template, session, redirect
from decimal import Decimal
from flask import session, redirect, render_template, flash

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect('/login')

    user_id = session['user']['user_id']

    db = get_db_connection()
    if not db:
        flash("Database temporarily unavailable.", "error")
        return redirect('/')

    try:
        cursor = db.cursor(dictionary=True)
        formatted_orders = []

        # Fetch standard orders
        cursor.execute("""
            SELECT order_id, smoothie, toast, icecream, workout,
                   addons, combo, quantity, total_bill,
                   reward_points_used, reward_points_earned,
                   order_time, payment_mode
            FROM orders
            WHERE user_id=%s
            ORDER BY order_time DESC
        """, (user_id,))
        all_orders = cursor.fetchall()

        # Fetch customized orders
        cursor.execute("""
            SELECT order_id, base, ingredients, whey, toppings, addons,
                   total_price, reward_points_used, reward_points_earned,
                   order_time, payment_mode
            FROM customized_orders
            WHERE user_id=%s
            ORDER BY order_time DESC
        """, (user_id,))
        custom_orders = cursor.fetchall()

        # Format standard orders
        for order in all_orders:
            if order.get('icecream'):
                item_name = order['icecream'] + " (Ice-Cream Order)"
            elif order.get('toast'):
                item_name = order['toast'] + " (Toast Order)"
            elif order.get('workout'):
                item_name = order['workout'] + " (Refreshment Drink Order)"
            else:
                item_name = (order['smoothie'] or "N/A")

            if order.get('combo'):
                item_name += f" | Combo: {order['combo']}"

            addons_str = order['addons'] if order['addons'] else "None"
            total_final = f"₹{float(order['total_bill']):.2f}"
            order_time = (
                order['order_time'].strftime("%d %b %Y, %I:%M %p")
                if order['order_time'] else "N/A"
            )

            formatted_orders.append({
                'order_id': order['order_id'],
                'smoothie': item_name,
                'addons': addons_str,
                'order_time': order_time,
                'total_bill': total_final,
                'payment_status': f"Paid via {order['payment_mode']}" if order['payment_mode'] else "Awaiting Payment",
            })

        # Format customized orders
        for order in custom_orders:
            parts = [order['base'], order['whey']]
            if order['ingredients']:
                parts.append(order['ingredients'])
            if order['toppings']:
                parts.append(f"Toppings: {order['toppings']}")

            smoothie_label = ", ".join(parts) + " (Custom Smoothie)"
            addons_str = order['addons'] if order['addons'] else "None"
            total_final = f"₹{float(order['total_price']):.2f}"
            order_time = (
                order['order_time'].strftime("%d %b %Y, %I:%M %p")
                if order['order_time'] else "N/A"
            )

            formatted_orders.append({
                'order_id': f"C{order['order_id']}",
                'smoothie': smoothie_label,
                'addons': addons_str,
                'order_time': order_time,
                'total_bill': total_final,
                'payment_status': f"Paid via {order['payment_mode']}" if order['payment_mode'] else "Awaiting Payment",
            })

        # Sort combined list
        formatted_orders.sort(
            key=lambda x: datetime.strptime(x['order_time'], "%d %b %Y, %I:%M %p"),
            reverse=True
        )

        return render_template(
            'profile.html',
            user=session['user'],
            orders=formatted_orders
        )

    except Exception:
        import traceback
        traceback.print_exc()
        flash("Error loading profile data.", "error")
        return redirect('/')

    finally:
        cursor.close()
        db.close()


def confirm_payment(order_id, payment_mode):
    db = get_db_connection()
    if not db:
        print("❌ DB unavailable during payment confirmation")
        return False

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM orders WHERE order_id=%s", (order_id,))
        order = cursor.fetchone()
        if not order:
            print(f"No order found with ID {order_id}")
            return False

        cursor.execute("UPDATE orders SET payment_mode=%s WHERE order_id=%s", (payment_mode, order_id))
        db.commit()
        print(f"✅ Payment confirmed for order {order_id}")
        return True

    except Exception as e:
        print("❌ Payment confirmation error:", e)
        db.rollback()
        return False

    finally:
        cursor.close()
        db.close()







@app.route('/reviews', methods=['GET'])
def reviews():
    db = get_db_connection()
    if not db:
        flash("Database temporarily unavailable.", "error")
        return redirect('/')

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM reviews ORDER BY created_at DESC")
        reviews = cursor.fetchall()
    except Exception as e:
        print("❌ Error fetching reviews:", e)
        reviews = []
    finally:
        cursor.close()
        db.close()

    return render_template('index.html', reviews=reviews)


@app.route('/submit_review', methods=['POST'])
def submit_review():
    try:
        user_id = session['user']['user_id'] if 'user' in session else None
        name = request.form.get('name')
        comment = request.form.get('comment')

        if not name or not comment:
            flash("Please fill in all required fields.", "error")
            return redirect('/')

        db = get_db_connection()
        if not db:
            flash("Database temporarily unavailable.", "error")
            return redirect('/')

        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("""
                INSERT INTO reviews (user_id, name, comment)
                VALUES (%s, %s, %s)
            """, (user_id, name, comment))
            db.commit()
            flash("Thank you for your review!", "success")
        finally:
            cursor.close()
            db.close()

    except Exception:
        import traceback
        traceback.print_exc()
        flash("Could not submit review. Try again.", "error")

    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
