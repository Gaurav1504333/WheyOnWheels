from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import mysql.connector
from datetime import datetime
import traceback
import os

app = Flask(__name__)
app.secret_key = 'b1e2c3d4a5f67890123456789abcdef'

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


# Google Sheet CSV export URL
Smoothie_MENU_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSob3Z4VWarQN4fiwdWX3UjH35ZsGddD5oGQXvd0FVqkg-NQw9GkCzLeXyVQeakmLzeZvIfXYace_3C/pub?output=csv"
Toast_MENU_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSg9CzlFJnSNaL_VTcI0X7D5w_tbsc6Yr0dyrTH9-8Sj_-xaU13gFEnUygd1v4GKwQWvu-iaqFdzwRb/pub?output=csv"
Workout_MENU_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRo6yrMCi9ZemNFmd_P91rTd5jp2VBWPE1xi-HMWk6hMo1eQGD_6NIfOaxew5wXZaNNZMqITLmbflmK/pub?output=csv"
ICECREAM_MENU_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTGMpB5gjOd0uMLhYUSuvW-tsav2YHEtqwDVGBiVME6rdoZJbwCwFkcueaWsbf1NUUo6Lzg00fjqh6z/pub?output=csv"
# Make 'user' globally available in templates
@app.context_processor
def inject_user():
    return dict(user=session.get('user'))

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

    user_id = session['user']['user_id']

    # -------------------------------------------------
    # Load menu
    # -------------------------------------------------
    try:
        df = pd.read_csv(Smoothie_MENU_CSV_URL)
        df.fillna('', inplace=True)
        smoothies = df.iloc[0:24, 1].dropna().tolist()
        addons = df.iloc[24:31, 1].dropna().tolist()
        prices = df.set_index(df.columns[1])[df.columns[4]].to_dict()
    except Exception as e:
        print("❌ Dropdown load error:", e)
        smoothies, addons, prices = [], [], {}

    # -------------------------------------------------
    # Fetch user's reward points (SAFE)
    # -------------------------------------------------
    user_rewards = 0
    db = get_db_connection()
    if db:
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT points FROM rewards WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            user_rewards = int(result['points']) if result and result.get('points') is not None else 0
        except Exception as e:
            print("❌ Reward fetch error:", e)
            user_rewards = 0
        finally:
            cursor.close()
            db.close()

    # -------------------------------------------------
    # Handle POST (order submission)
    # -------------------------------------------------
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

        try:
            redeem_points = int(request.form.get('redeem_points', 0))
        except:
            redeem_points = 0

        # Build order details
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

        # -------------------------------------------------
        # Calculate total
        # -------------------------------------------------
        total_bill = 0.0
        total_smoothies = 0

        for s, q in zip(smoothie_list, quantity_list):
            if s and s.strip() and q and q.strip().isdigit():
                price = float(prices.get(s.strip(), 0) or 0)
                qty = int(q.strip())
                total_bill += price * qty
                total_smoothies += qty

        for a in addon_list:
            if a and a.strip():
                addon_price = float(prices.get(a.strip(), 0) or 0)
                total_bill += addon_price

        if total_smoothies >= 2:
            total_bill *= 0.9

        total_bill = round(total_bill, 2)

        # -------------------------------------------------
        # Rewards
        # -------------------------------------------------
        reward_used = min(redeem_points, total_bill, user_rewards)
        total_after_rewards = round(total_bill - reward_used, 2)
        reward_earned = int(round(total_after_rewards * 0.06))

        # -------------------------------------------------
        # Save pending order in session
        # -------------------------------------------------
        session['pending_order'] = {
            'type': 'normal',
            'category': 'smoothie',
            'smoothie': smoothie_str,
            'addons': addon_str,
            'quantity': ','.join(quantity_list),
            'total_bill': total_bill,
            'smoothie_price': total_bill,
            'reward_used': reward_used,
            'reward_earned': reward_earned,
            'total_after_rewards': total_after_rewards
        }

        flash(f"Smoothie order added. Total after rewards: ₹{total_after_rewards}", "info")
        return redirect('/payment_page')

    # -------------------------------------------------
    # GET request
    # -------------------------------------------------
    return render_template(
        'order_smoothie.html',
        smoothies=smoothies,
        addons=addons,
        prices=prices,
        user_rewards=user_rewards
    )

    
@app.route('/order_toast', methods=['GET', 'POST'])
def order_toast():
    if 'user' not in session:
        return redirect('/login')

    user_id = session['user']['user_id']

    try:
        df = pd.read_csv(Toast_MENU_CSV_URL)
        df.fillna('', inplace=True)

        # Toast names for dropdown
        toasts = df.iloc[0:15, 1].dropna().tolist()

        # 🔥 SAFELY detect price column
        price_col = df.columns[4]

        # Clean price column
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

    # ---------------------------------
    # Fetch user rewards (SAFE)
    # ---------------------------------
    user_rewards = 0
    db = get_db_connection()
    if db:
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT points FROM rewards WHERE user_id=%s", (user_id,))
            result = cursor.fetchone()
            user_rewards = int(result['points']) if result and result.get('points') is not None else 0
        except Exception as e:
            print("❌ Reward fetch error:", e)
            user_rewards = 0
        finally:
            cursor.close()
            db.close()

    # ---------------------------------
    # POST → submit order
    # ---------------------------------
    if request.method == 'POST':
        toast_list = request.form.getlist('toast[]')
        quantity_list = request.form.getlist('quantity[]')

        try:
            redeem_points = int(request.form.get('redeem_points', 0))
        except:
            redeem_points = 0

        toast_data = [
            f"{t.strip()} x{q.strip()}"
            for t, q in zip(toast_list, quantity_list)
            if t and t.strip() and q and q.strip().isdigit()
        ]

        toast_str = ', '.join(toast_data)

        if not toast_str:
            flash("Please select at least one toast item.", "error")
            return redirect('/order_toast')

        # ---------------------------------
        # Calculate total bill
        # ---------------------------------
        total_bill = 0.0
        total_items = 0

        for t, q in zip(toast_list, quantity_list):
            if t and t.strip() and q and q.strip().isdigit():
                qty = int(q.strip())
                key = t.strip().lower()
                price = prices_backend.get(key, 0)
                total_bill += price * qty
                total_items += qty

        if total_items >= 2:
            total_bill *= 0.9

        total_bill = round(total_bill, 2)

        # ---------------------------------
        # Rewards
        # ---------------------------------
        reward_used = min(redeem_points, total_bill, user_rewards)
        total_after_rewards = round(total_bill - reward_used, 2)
        reward_earned = int(round(total_after_rewards * 0.06))

        # ---------------------------------
        # Save pending order
        # ---------------------------------
        session['pending_order'] = {
            'type': 'normal',
            'category': 'toast',
            'toast': toast_str,
            'smoothie': '',
            'addons': '',
            'combo': '',
            'quantity': ','.join(quantity_list),
            'total_bill': total_bill,
            'reward_used': reward_used,
            'reward_earned': reward_earned,
            'total_after_rewards': total_after_rewards
        }

        flash(f"Toast order added. Total after rewards: ₹{total_after_rewards}", "info")
        return redirect('/payment_page')

    # ---------------------------------
    # Render page
    # ---------------------------------
    return render_template(
        'order_toast.html',
        toasts=toasts,
        prices=prices_frontend,
        user_rewards=user_rewards
    )



from itertools import zip_longest

@app.route('/order_workout', methods=['GET', 'POST'])
def order_workout():
    if 'user' not in session:
        return redirect('/login')

    user_id = session['user']['user_id']

    # -------------------------------------------------
    # Load menu
    # -------------------------------------------------
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

    # -------------------------------------------------
    # Get rewards balance (SAFE)
    # -------------------------------------------------
    user_rewards = 0
    db = get_db_connection()
    if db:
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT points FROM rewards WHERE user_id=%s", (user_id,))
            result = cursor.fetchone()
            user_rewards = int(result['points']) if result and result.get('points') else 0
        except Exception as e:
            print("❌ Reward fetch error:", e)
            user_rewards = 0
        finally:
            cursor.close()
            db.close()

    # -------------------------------------------------
    # POST REQUEST
    # -------------------------------------------------
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

        try:
            redeem_points = int(request.form.get('redeem_points', 0))
        except:
            redeem_points = 0

        # -------------------------------------------------
        # Total Calculation
        # -------------------------------------------------
        total_bill = 0.0
        total_items = 0
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
            total_items += qty
            workout_display.append(f"{w} x{qty}")

            # Addon calculated per qty
            if a:
                addon_price = float(prices.get(a, 0))
                total_bill += addon_price * qty

        # Combo pricing
        if combo:
            total_bill += float(prices.get(combo, 0)) * max(combo_qty, 1)
            total_items += max(combo_qty, 1)

        if combo_addon:
            total_bill += float(prices.get(combo_addon, 0)) * max(combo_qty, 1)

        # Quantity discount
        discount_applied = False
        if total_items >= 2:
            total_bill *= 0.90
            discount_applied = True

        total_bill = round(total_bill, 2)

        # -------------------------------------------------
        # Rewards Calculation
        # -------------------------------------------------
        reward_used = min(redeem_points, user_rewards, total_bill)
        total_after_rewards = round(total_bill - reward_used, 2)
        reward_earned = int(round(total_after_rewards * 0.06))

        # -------------------------------------------------
        # Save to session
        # -------------------------------------------------
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
            'discount_applied': discount_applied,

            # Required in payment_page
            'reward_used': reward_used,
            'reward_earned': reward_earned,
            'total_after_rewards': total_after_rewards
        }

        return redirect('/payment_page')

    # GET REQUEST
    return render_template(
        'order_workout.html',
        workouts=workouts,
        addons=addons,
        combos=combos,
        prices=prices,
        user_rewards=user_rewards
    )




# ----------------- ORDER CUSTOMIZE -----------------
@app.route('/order_customize', methods=['GET', 'POST'])
def order_customize():
    if 'user' not in session:
        return redirect('/login')
    user_id = session['user']['user_id']

    grouped = {
        'base': [
            {'name': 'Low-Fat Milk (250ml)', 'price': 20, 'macros': {'cal': 95, 'protein': 6, 'carbs': 9, 'fat': 3}},
            {'name': 'Water (250ml)', 'price': 10, 'macros': {'cal': 0, 'protein': 0, 'carbs': 0, 'fat': 0}},
            {'name': 'Water + Low-Fat Milk (125ml+125ml)', 'price': 15, 'macros': {'cal': 47, 'protein': 3, 'carbs': 4, 'fat': 1.5}}
        ],
        'ingredients': [
            {'name': 'Frozen Banana', 'price': 10, 'macros': {'cal': 89, 'protein': 1.1, 'carbs': 23, 'fat': 0.3}},
            {'name': 'Frozen Alphonso Mango Slice', 'price': 25, 'macros': {'cal': 60, 'protein': 0.8, 'carbs': 15, 'fat': 0.2}},
            {'name': 'Frozen Pineapple Slice', 'price': 25, 'macros': {'cal': 50, 'protein': 0.5, 'carbs': 13, 'fat': 0.1}},
            {'name': 'Frozen Strawberry', 'price': 30, 'macros': {'cal': 35, 'protein': 0.7, 'carbs': 8, 'fat': 0.3}},
            {'name': 'Frozen Blueberry', 'price': 30, 'macros': {'cal': 42, 'protein': 0.5, 'carbs': 11, 'fat': 0.2}},
            {'name': 'Avacado Frozen Halves', 'price': 40, 'macros': {'cal': 120, 'protein': 1.5, 'carbs': 6, 'fat': 10}}
        ],
        'whey': [
  {
    'name': 'Half Scoop – Belgian Chocolate Whey',
    'price': 60,
    'macros': {'cal': 60, 'protein': 12, 'carbs': 1.5, 'fat': 1}
  },
  {
    'name': 'Full Scoop – Belgian Chocolate Whey',
    'price': 100,
    'macros': {'cal': 120, 'protein': 24, 'carbs': 3, 'fat': 2}
  },

  {
    'name': 'Half Scoop – Chocolate Hazelnut Whey',
    'price': 60,
    'macros': {'cal': 60, 'protein': 12, 'carbs': 1.5, 'fat': 1}
  },
  {
    'name': 'Full Scoop – Chocolate Hazelnut Whey',
    'price': 100,
    'macros': {'cal': 120, 'protein': 24, 'carbs': 3, 'fat': 2}
  },

  {
    'name': 'Half Scoop – Bold Cold Coffee Whey',
    'price': 60,
    'macros': {'cal': 60, 'protein': 12, 'carbs': 1.5, 'fat': 1}
  },
  {
    'name': 'Full Scoop – Bold Cold Coffee Whey',
    'price': 100,
    'macros': {'cal': 120, 'protein': 24, 'carbs': 3, 'fat': 2}
  },

  {
    'name': 'Half Scoop – Traditional Malai Kulfi Whey',
    'price': 60,
    'macros': {'cal': 60, 'protein': 12, 'carbs': 1.5, 'fat': 1}
  },
  {
    'name': 'Full Scoop – Traditional Malai Kulfi Whey',
    'price': 100,
    'macros': {'cal': 120, 'protein': 24, 'carbs': 3, 'fat': 2}
  },

  {
    'name': 'Half Scoop – Creamy Caramel Crème Whey',
    'price': 60,
    'macros': {'cal': 60, 'protein': 12, 'carbs': 1.5, 'fat': 1}
  },
  {
    'name': 'Full Scoop – Creamy Caramel Crème Whey',
    'price': 100,
    'macros': {'cal': 120, 'protein': 24, 'carbs': 3, 'fat': 2}
  },

  {
    'name': 'Half Scoop – Raw Whey',
    'price': 60,
    'macros': {'cal': 55, 'protein': 13, 'carbs': 1, 'fat': 0.5}
  },
  {
    'name': 'Full Scoop – Raw Whey',
    'price': 100,
    'macros': {'cal': 110, 'protein': 26, 'carbs': 2, 'fat': 1}
  },

  {
    'name': 'Half Scoop – Mango Whey',
    'price': 60,
    'macros': {'cal': 62, 'protein': 12, 'carbs': 2, 'fat': 1}
  },
  {
    'name': 'Full Scoop – Mango Whey',
    'price': 100,
    'macros': {'cal': 124, 'protein': 24, 'carbs': 4, 'fat': 2}
  }

        ],
        'toppings': [
            {'name': 'Choco Chips', 'price': 10, 'macros': {'cal': 70, 'protein': 0.5, 'carbs': 9, 'fat': 4}},
            {'name': 'Cocoa', 'price': 15, 'macros': {'cal': 20, 'protein': 1, 'carbs': 3, 'fat': 0.5}},
            {'name': 'Dates', 'price': 15, 'macros': {'cal': 66, 'protein': 0.6, 'carbs': 18, 'fat': 0.1}},
            {'name': 'Cardamom', 'price': 15, 'macros': {'cal': 18, 'protein': 0.6, 'carbs': 4, 'fat': 0.3}}
        ],
        'addons': [
            {'name': 'Creatine', 'price': 25, 'macros': {'cal': 0, 'protein': 0, 'carbs': 0, 'fat': 0}},
            {'name': 'Extra Fruit Shot', 'price': 30, 'macros': {'cal': 40, 'protein': 0.3, 'carbs': 10, 'fat': 0}},
            {'name': 'Nut Butter Drizzle', 'price': 15, 'macros': {'cal': 90, 'protein': 3, 'carbs': 2, 'fat': 8}},
            {'name': 'Oats/Fiber Boost', 'price': 20, 'macros': {'cal': 80, 'protein': 3, 'carbs': 14, 'fat': 1.5}}
        ]
    }

    if request.method == 'POST':
        base = request.form.get('base')
        ingredients = request.form.get('ingredients')
        whey = request.form.get('whey')
        toppings = request.form.get('toppings') or ""
        addons = request.form.get('addons') or ""

        # ✅ Calculate total price
        total = 0
        for category, choice in [('base', base), ('ingredients', ingredients), ('whey', whey), ('toppings', toppings), ('addons', addons)]:
            for item in grouped[category]:
                if item['name'] == choice:
                    total += item['price']
                    break
        total = round(total, 2)

        # ✅ Save order details (no rewards)
        session['pending_order'] = {
            'type': 'customized',
            'category': 'customize',
            'base': base,
            'ingredients': ingredients,
            'whey': whey,
            'toppings': toppings,
            'addons': addons,
            'total_bill': total
        }

        flash(f"Custom smoothie added. Payable amount: ₹{total}", "info")
        return redirect('/payment_page')

    # ✅ Render page
    return render_template('order_customize.html', grouped=grouped)

@app.route('/order_icecream', methods=['GET', 'POST'])
def order_icecream():
    if 'user' not in session:
        return redirect('/login')

    user_id = session['user']['user_id']

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

    # ---------------------------------
    # Fetch user rewards (SAFE)
    # ---------------------------------
    user_rewards = 0
    db = get_db_connection()
    if db:
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT points FROM rewards WHERE user_id=%s", (user_id,))
            result = cursor.fetchone()
            user_rewards = int(result['points']) if result and result.get('points') is not None else 0
        except Exception as e:
            print("❌ Reward fetch error:", e)
            user_rewards = 0
        finally:
            cursor.close()
            db.close()

    # -----------------------------
    # POST → submit order
    # -----------------------------
    if request.method == 'POST':
        icecream_list = request.form.getlist('icecream[]')
        quantity_list = request.form.getlist('quantity[]')

        try:
            redeem_points = int(request.form.get('redeem_points', 0))
        except:
            redeem_points = 0

        icecream_data = [
            f"{item} x{qty}"
            for item, qty in zip(icecream_list, quantity_list)
            if item and qty.isdigit()
        ]

        icecream_str = ", ".join(icecream_data)

        if not icecream_str:
            flash("Please select at least one icecream item.", "error")
            return redirect('/order_icecream')

        # Calculate total bill
        total_bill = 0
        total_items = 0

        for item, qty in zip(icecream_list, quantity_list):
            if item and qty.isdigit():
                qty = int(qty)
                price = float(prices.get(item, 0))
                total_bill += price * qty
                total_items += qty

        if total_items >= 2:
            total_bill *= 0.90

        total_bill = round(total_bill, 2)

        # Reward logic
        reward_used = min(redeem_points, user_rewards, total_bill)
        total_after_rewards = round(total_bill - reward_used, 2)
        reward_earned = int(round(total_after_rewards * 0.06))

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
            'reward_used': reward_used,
            'reward_earned': reward_earned,
            'total_after_rewards': total_after_rewards
        }

        return redirect('/payment_page')

    return render_template(
        'order_icecream.html',
        icecreams=icecreams,
        prices=prices,
        user_rewards=user_rewards
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

        # ---------------------- REWARD LOAD --------------------------
        cursor.execute("SELECT points FROM rewards WHERE user_id=%s", (user_id,))
        result = cursor.fetchone()

        if not result:
            cursor.execute("INSERT INTO rewards (user_id, points) VALUES (%s, 0)", (user_id,))
            db.commit()
            current_rewards = 0
        else:
            current_rewards = int(result["points"])

        # ---------------------- OPERATORS ----------------------------
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

        def safe_int(v, f=0):
            try: return int(float(v))
            except: return f

        total_bill = safe_float(pending_order.get("total_bill"))
        reward_used = safe_int(pending_order.get("reward_used"))
        reward_earned = safe_int(pending_order.get("reward_earned"))

        reward_used = min(reward_used, current_rewards)
        total_after_rewards = round(max(total_bill - reward_used, 0), 2)

        # ------------------------- POST -------------------------------
        if request.method == "POST":
            operator_code_form = request.form.get("operator_code", "").strip()
            payment_mode = request.form.get("payment_mode", "").lower()

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

            # ----------------- UPDATE REWARDS ---------------------
            new_points = max(current_rewards - reward_used, 0) + reward_earned
            cursor.execute(
                "UPDATE rewards SET points=%s WHERE user_id=%s",
                (new_points, user_id)
            )

            # ----------------- INSERT ORDER ------------------------------
            order_type = pending_order.get("type", "normal")

            if order_type == "customized":
                cursor.execute("""
                    INSERT INTO customized_orders (
                        user_id, base, ingredients, whey, toppings, addons,
                        total_price, reward_points_used, reward_points_earned,
                        payment_mode
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    user_id,
                    pending_order.get("base"),
                    pending_order.get("ingredients"),
                    pending_order.get("whey"),
                    pending_order.get("toppings"),
                    pending_order.get("addons"),
                    total_after_rewards,
                    reward_used,
                    reward_earned,
                    payment_mode
                ))

                order_id = cursor.lastrowid

            else:
                qty_raw = pending_order.get("quantity_list") or pending_order.get("quantity") or "1"
                quantity_clean = ",".join(qty_raw) if isinstance(qty_raw, list) else str(qty_raw)

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
                    total_after_rewards,
                    reward_used,
                    reward_earned,
                    payment_mode
                ))

                order_id = cursor.lastrowid

            # ----------------- OPERATOR LOG ------------------------------
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
                    total_after_rewards,
                    payment_mode,
                    order_type
                ))

            db.commit()

            for k in ["pending_order", "valid_code_entered",
                      "operator_code", "operator_name", "operator_location"]:
                session.pop(k, None)

            flash(f"Payment successful! Paid ₹{total_after_rewards}", "success")
            return redirect("/profile")

        # ------------------ GET ----------------------
        order_for_display = pending_order.copy()
        order_for_display["total_bill"] = total_after_rewards

        return render_template(
            "payment_page.html",
            order=order_for_display,
            valid_code_entered=valid_code_entered,
            operator_name=operator_name,
            operator_code=operator_code,
            operator_location=operator_location,
            current_rewards=current_rewards,
            total_bill=total_bill,
            total_after_rewards=total_after_rewards,
            reward_used=reward_used,
            reward_earned=reward_earned
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

        # --------------------
        # Basic Validations
        # --------------------
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

        # --------------------
        # Insert Into Database (SAFE)
        # --------------------
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

        # --------------------------------------------
        # FETCH STANDARD ORDERS
        # --------------------------------------------
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

        # --------------------------------------------
        # FETCH CUSTOMIZED SMOOTHIES
        # --------------------------------------------
        cursor.execute("""
            SELECT order_id, base, ingredients, whey, toppings, addons,
                   total_price, reward_points_used, reward_points_earned,
                   order_time, payment_mode
            FROM customized_orders
            WHERE user_id=%s
            ORDER BY order_time DESC
        """, (user_id,))
        custom_orders = cursor.fetchall()

        # --------------------------------------------
        # FORMAT STANDARD ORDERS
        # --------------------------------------------
        for order in all_orders:

            if order.get('icecream'):
                item_name = order['icecream'] + " (Ice-Cream Order)"
            elif order.get('toast'):
                item_name = order['toast'] + " (Toast Order)"
            elif order.get('workout'):
                item_name = order['workout'] + " (Workout Order)"
            else:
                item_name = (order['smoothie'] or "N/A")

            if order.get('combo'):
                item_name += f" | Combo: {order['combo']}"

            addons_str = order['addons'] if order['addons'] else "None"

            rewards_used = int(order['reward_points_used'] or 0)
            reward_text = f" ({rewards_used} pts used)" if rewards_used else ""
            total_final = f"₹{float(order['total_bill']):.2f}{reward_text}"

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
                'rewards_used': rewards_used,
                'rewards_earned': int(order['reward_points_earned'] or 0),
                'payment_status': f"Paid via {order['payment_mode']}" if order['payment_mode'] else "Awaiting Payment",
            })

        # --------------------------------------------
        # FORMAT CUSTOMIZED ORDERS
        # --------------------------------------------
        for order in custom_orders:

            parts = [order['base'], order['whey']]
            if order['ingredients']:
                parts.append(order['ingredients'])
            if order['toppings']:
                parts.append(f"Toppings: {order['toppings']}")

            smoothie_label = ", ".join(parts) + " (Custom Smoothie)"

            addons_str = order['addons'] if order['addons'] else "None"

            rewards_used = int(order['reward_points_used'] or 0)
            reward_text = f" ({rewards_used} pts used)" if rewards_used else ""
            total_final = f"₹{float(order['total_price']):.2f}{reward_text}"

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
                'rewards_used': rewards_used,
                'rewards_earned': int(order['reward_points_earned'] or 0),
                'payment_status': f"Paid via {order['payment_mode']}" if order['payment_mode'] else "Awaiting Payment",
            })

        # --------------------------------------------
        # SORT FINAL ORDER LIST
        # --------------------------------------------
        formatted_orders.sort(
            key=lambda x: datetime.strptime(x['order_time'], "%d %b %Y, %I:%M %p"),
            reverse=True
        )

        # --------------------------------------------
        # REWARD BALANCE
        # --------------------------------------------
        cursor.execute("SELECT points FROM rewards WHERE user_id=%s", (user_id,))
        result = cursor.fetchone()

        if not result:
            cursor.execute("INSERT INTO rewards (user_id, points) VALUES (%s, 0)", (user_id,))
            db.commit()
            current_rewards = 0
        else:
            current_rewards = int(result['points'])

        # --------------------------------------------
        # SPIN MILESTONE LOGIC
        # --------------------------------------------
        total_orders = len(formatted_orders)
        milestone = None
        claimed = False

        if total_orders > 0 and total_orders % 5 == 0:
            milestone = total_orders
            cursor.execute("""
                SELECT 1 FROM spin_claims
                WHERE user_id=%s AND milestone=%s
            """, (user_id, milestone))
            claimed = cursor.fetchone() is not None

        # --------------------------------------------
        # RENDER PAGE
        # --------------------------------------------
        return render_template(
            'profile.html',
            user=session['user'],
            orders=formatted_orders,
            current_rewards=current_rewards,
            milestone=milestone,
            claimed=claimed
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
    """
    Call this function once payment is successful.
    Updates the order's payment_mode and adds earned reward points to user's account.
    """
    db = get_db_connection()
    if not db:
        print("❌ DB unavailable during payment confirmation")
        return False

    try:
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT user_id, reward_points_earned FROM orders WHERE order_id=%s", (order_id,))
        order = cursor.fetchone()
        if not order:
            print(f"No order found with ID {order_id}")
            return False

        user_id = order['user_id']
        earned_points = int(order['reward_points_earned'] or 0)

        cursor.execute("UPDATE orders SET payment_mode=%s WHERE order_id=%s", (payment_mode, order_id))

        if earned_points > 0:
            cursor.execute("UPDATE rewards SET points = points + %s WHERE user_id=%s", (earned_points, user_id))

        db.commit()
        print(f"✅ Payment confirmed and {earned_points} reward points added for user {user_id}")
        return True

    except Exception as e:
        print("❌ Payment confirmation error:", e)
        db.rollback()
        return False

    finally:
        cursor.close()
        db.close()

    
    
@app.route("/claim_spin", methods=["POST"])
def claim_spin():
    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]["user_id"]
    milestone = int(request.form["milestone"])

    SPIN_REWARD_POINTS = 25

    db = get_db_connection()
    if not db:
        flash("Database temporarily unavailable.", "error")
        return redirect("/profile")

    try:
        cursor = db.cursor(dictionary=True)

        # Prevent duplicate claim
        cursor.execute("""
            SELECT 1 FROM spin_claims WHERE user_id=%s AND milestone=%s
        """, (user_id, milestone))

        if cursor.fetchone():
            flash("Spin already claimed.", "error")
            return redirect("/profile")

        # Insert claim
        cursor.execute("""
            INSERT INTO spin_claims (user_id, milestone, claimed)
            VALUES (%s, %s, TRUE)
        """, (user_id, milestone))

        # Add reward
        cursor.execute("""
            INSERT INTO rewards (user_id, points)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE points = points + VALUES(points)
        """, (user_id, SPIN_REWARD_POINTS))

        db.commit()

        flash(f"You earned {SPIN_REWARD_POINTS} points!", "success")
        return redirect("/profile")

    finally:
        cursor.close()
        db.close()

@app.route('/verify_spin', methods=['GET', 'POST'])
def verify_spin():
    if 'user' not in session:
        return redirect('/login')

    import requests, csv, io, time

    user_id = session['user']['user_id']
    milestone = request.args.get('milestone') or request.form.get('milestone')

    if not milestone:
        flash("Invalid milestone.", "error")
        return redirect('/profile')

    milestone = int(milestone)

    db = get_db_connection()
    if not db:
        flash("Database temporarily unavailable.", "error")
        return redirect('/profile')

    try:
        cursor = db.cursor(dictionary=True)

        # -------------------------------------------------------
        # Prevent duplicate verification
        # -------------------------------------------------------
        cursor.execute("""
            SELECT 1 FROM spin_claims 
            WHERE user_id=%s AND milestone=%s AND claimed=TRUE
        """, (user_id, milestone))

        if cursor.fetchone():
            flash("This spin is already verified.", "error")
            return redirect("/profile")

        # -------------------------------------------------------
        # Ensure rewards row
        # -------------------------------------------------------
        cursor.execute("""
            INSERT IGNORE INTO rewards (user_id, points)
            VALUES (%s, 0)
        """, (user_id,))
        db.commit()

        # -------------------------------------------------------
        # Load operator sheet
        # -------------------------------------------------------
        SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQrzOKK1RFl-aMdq36fi6W79p1YUgMbKYqShXQCitS7klGY_24KBeTHTsoAPsCjs_zzFEF2l8AjebhN/pub?output=csv"

        operator_data = {}
        sheet_loaded = False

        try:
            r = requests.get(SHEET_URL, timeout=6)
            r.raise_for_status()
            csv_rows = list(csv.reader(io.StringIO(r.text)))

            for row in csv_rows[1:]:
                if len(row) >= 3:
                    code = row[1].strip()
                    operator_data[code] = {
                        "name": row[0].strip(),
                        "location": row[2].strip()
                    }

            sheet_loaded = True

        except Exception as e:
            print("Sheet error:", e)
            flash("Could not load operator data.", "error")

        # -------------------------------------------------------
        # Session temp values
        # -------------------------------------------------------
        valid_code = session.get('spin_valid_code', False)
        operator_name = session.get('spin_operator_name', '')
        operator_code = session.get('spin_operator_code', '')
        operator_location = session.get('spin_operator_location', '')

        # -------------------------------------------------------
        # POST logic
        # -------------------------------------------------------
        if request.method == 'POST':
            form_code = (request.form.get('operator_code') or '').strip()
            form_points = (request.form.get('reward_points') or '').strip()

            # ---------------- STEP 1: Verify operator ----------------
            if form_code and not form_points:
                if not sheet_loaded:
                    flash("Operator sheet not loaded.", "error")
                    return redirect(f"/verify_spin?milestone={milestone}")

                match = operator_data.get(form_code)
                if not match:
                    flash("Invalid operator code.", "error")
                    return redirect(f"/verify_spin?milestone={milestone}")

                session['spin_valid_code'] = True
                session['spin_operator_code'] = form_code
                session['spin_operator_name'] = match['name']
                session['spin_operator_location'] = match['location']
                session['__force_update'] = str(time.time())

                flash(f"Operator verified: {match['name']}", "success")
                return redirect(f"/verify_spin?milestone={milestone}")

            # ---------------- STEP 2: Add reward ----------------
            if form_points == "":
                flash("Enter reward points.", "error")
                return redirect(f"/verify_spin?milestone={milestone}")

            try:
                form_points = int(form_points)
            except:
                flash("Reward points must be a number.", "error")
                return redirect(f"/verify_spin?milestone={milestone}")

            if not operator_code:
                flash("Verify operator first.", "error")
                return redirect(f"/verify_spin?milestone={milestone}")

            # -------------------------------------------------------
            # Final duplicate protection
            # -------------------------------------------------------
            cursor.execute("""
                SELECT 1 FROM spin_claims 
                WHERE user_id=%s AND milestone=%s AND claimed=TRUE
            """, (user_id, milestone))

            if cursor.fetchone():
                flash("This spin is already verified.", "error")
                return redirect("/profile")

            # -------------------------------------------------------
            # Insert claim
            # -------------------------------------------------------
            cursor.execute("""
                INSERT INTO spin_claims 
                (user_id, milestone, claimed, reward_points, operator_name, operator_code, operator_location)
                VALUES (%s, %s, TRUE, %s, %s, %s, %s)
            """, (user_id, milestone, form_points, operator_name, operator_code, operator_location))

            # -------------------------------------------------------
            # Add reward points
            # -------------------------------------------------------
            cursor.execute("""
                INSERT INTO rewards (user_id, points)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE points = points + VALUES(points)
            """, (user_id, form_points))

            # -------------------------------------------------------
            # Log operator verification
            # -------------------------------------------------------
            cursor.execute("""
                INSERT INTO operator_spin_logs
                (user_id, milestone, operator_name, operator_code, operator_location, points_added)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                milestone,
                operator_name,
                operator_code,
                operator_location,
                form_points
            ))

            db.commit()

            # -------------------------------------------------------
            # Clear temp session
            # -------------------------------------------------------
            for k in ['spin_valid_code', 'spin_operator_name', 'spin_operator_code', 'spin_operator_location']:
                session.pop(k, None)

            flash(f"Spin Verified! +{form_points} points added.", "success")
            return redirect('/profile')

        # -------------------------------------------------------
        # GET render
        # -------------------------------------------------------
        return render_template(
            "verify_spin.html",
            milestone=milestone,
            valid_code_entered=valid_code,
            operator_name=operator_name,
            operator_location=operator_location,
            operator_code=operator_code
        )

    finally:
        cursor.close()
        db.close()



@app.route("/process_spin_verification", methods=["POST"])
def process_spin_verification():
    if 'user' not in session:
        return redirect('/login')

    user_id = session["user"]["user_id"]  # 🔥 FIXED SECURITY
    milestone = int(request.form.get("milestone"))
    operator_code_form = request.form.get("operator_code", "").strip()
    earned_points = int(request.form.get("earned_points", 0))

    import requests, csv, io

    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQrzOKK1RFl-aMdq36fi6W79p1YUgMbKYqShXQCitS7klGY_24KBeTHTsoAPsCjs_zzFEF2l8AjebhN/pub?output=csv"

    operator_data = {}

    try:
        res = requests.get(SHEET_URL, timeout=6)
        res.raise_for_status()
        csv_data = list(csv.reader(io.StringIO(res.text)))

        for row in csv_data[1:]:
            if len(row) >= 3:
                name, code, location = row[0].strip(), row[1].strip(), row[2].strip()
                operator_data[code] = {"name": name, "location": location}

    except Exception as e:
        print("⚠️ Operator Sheet Load Error:", e)
        flash("Error loading operator data!", "error")
        return redirect("/profile")

    if operator_code_form not in operator_data:
        flash("Invalid Operator Code!", "error")
        return redirect("/profile")

    operator_name = operator_data[operator_code_form]["name"]
    operator_location = operator_data[operator_code_form]["location"]

    db = get_db_connection()
    if not db:
        flash("Database temporarily unavailable.", "error")
        return redirect("/profile")

    try:
        cursor = db.cursor(dictionary=True)

        # Prevent duplicate claim
        cursor.execute("""
            SELECT 1 FROM spin_claims WHERE user_id=%s AND milestone=%s
        """, (user_id, milestone))

        if cursor.fetchone():
            flash("Spin already verified.", "error")
            return redirect("/profile")

        # Insert claim
        cursor.execute("""
            INSERT INTO spin_claims (user_id, milestone, claimed)
            VALUES (%s, %s, TRUE)
        """, (user_id, milestone))

        # Add reward
        cursor.execute("""
            INSERT INTO rewards (user_id, points)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE points = points + VALUES(points)
        """, (user_id, earned_points))

        # Log operator
        cursor.execute("""
            INSERT INTO operator_spin_logs 
            (user_id, milestone, operator_name, operator_code, operator_location, points_added)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            milestone,
            operator_name,
            operator_code_form,
            operator_location,
            earned_points
        ))

        db.commit()

        flash(f"🎉 Spin verified by {operator_name}! {earned_points} points added.", "success")
        return redirect("/profile")

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



#E:\wow\python.exe e:\wow\app.py 
from flask import send_from_directory

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')

