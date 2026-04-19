from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "fastbuy_secret_key"

# ================= DATABASE =================
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "fastbuy"
}

def get_db():
    return mysql.connector.connect(**db_config)

# ================= HELPERS =================
def get_user_by_email(email):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        if get_user_by_email(email):
            flash("Email already exists", "danger")
            return redirect(url_for("register"))

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name,email,password) VALUES (%s,%s,%s)",
            (name, email, password)
        )
        conn.commit()
        cur.close()
        conn.close()

        flash("Registration successful! Login now.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Please enter both email and password", "warning")
            return redirect(url_for("login"))

        # Hardcoded admin
        if email.lower() == "admin@gmail.com" and password == "admin123":
            session.clear()
            session["user_id"] = 0          # dummy ID for admin
            session["user_name"] = "Admin"
            session["user_role"] = "admin"
            flash("Admin login successful", "success")
            return redirect(url_for("admin_dashboard"))

        # Normal user login
        user = get_user_by_email(email)
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password", "danger")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = "user"
        flash("Login successful", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM products LIMIT 8")
    products = cur.fetchall()
    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        username=session["user_name"],
        products=products
    )

# ---------- CATEGORY ----------
# ---------- ALL CATEGORIES ----------
@app.route("/categories")
def all_categories():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    cur.close()
    conn.close()

    # Pass user from session
    user = None
    if "user_id" in session:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
        user = cur.fetchone()
        cur.close()
        conn.close()

    return render_template("category.html", categories=categories, user=user)




# ---------- CATEGORY PRODUCTS ----------
@app.route("/category/<int:category_id>")
def category_products(category_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM categories WHERE id=%s", (category_id,))
    category = cur.fetchone()

    cur.execute("SELECT * FROM products WHERE category_id=%s", (category_id,))
    products = cur.fetchall()

    cur.close()
    conn.close()

    cart = session.get("cart", {})

    total_items = sum(cart.values())
    total_price = 0

    if cart:
        conn = get_db()
        cur = conn.cursor()
        for pid, qty in cart.items():
            cur.execute("SELECT price FROM products WHERE id=%s", (pid,))
            price = cur.fetchone()[0]
            total_price += price * qty
        cur.close()
        conn.close()

    user = get_user_by_id(session["user_id"]) if "user_id" in session else None

    return render_template(
        "products.html",
        category=category,
        products=products,
        cart=cart,
        total_items=total_items,
        total_price=total_price,
        user=user
    )


@app.route("/update_cart", methods=["POST"])
def update_cart():
    data = request.get_json()
    pid = str(data["product_id"])
    change = int(data["change"])

    if "cart" not in session:
        session["cart"] = {}

    # ADD / UPDATE ITEM
    session["cart"][pid] = session["cart"].get(pid, 0) + change

    # REMOVE ITEM IF QTY <= 0
    if session["cart"][pid] <= 0:
        session["cart"].pop(pid)

    session.modified = True

    return jsonify({
        "success": True,
        "cart": session["cart"]
    })



# ---------- ORDERS ----------
@app.route("/orders")
def orders():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    user = cur.fetchone()

    cur.execute("""
        SELECT *
        FROM orders
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (session["user_id"],))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    orders = {}
    for r in rows:
        oid = r["id"]
        if oid not in orders:
            orders[oid] = {
                "id": oid,
                "status": r["status"],
                "created_at": r["created_at"],
                "products": [],
                "total_amount": 0
            }

        orders[oid]["products"].append({
            "name": r["product_name"],
            "image": r["product_image"],  # ✅ NOW EXISTS
            "quantity": r["quantity"],
            "price": r["price"]
        })

        orders[oid]["total_amount"] += r["price"]

    return render_template(
        "orders.html",
        user=user,
        orders=list(orders.values())
    )


# ---------- PRODUCT DETAILS ----------
# ---------- PRODUCT DETAILS ----------
@app.route('/product/<int:product_id>')
def product_detail(product_id):

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # ================= PRODUCT =================
    cursor.execute("SELECT * FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return "Product not found", 404

    # ================= FEATURES =================
    cursor.execute("""
        SELECT feature 
        FROM product_features 
        WHERE product_id=%s
    """, (product_id,))
    product["features"] = [row["feature"] for row in cursor.fetchall()]

    # ================= SPECIFICATIONS =================
    cursor.execute("""
        SELECT spec_key, spec_value 
        FROM product_specifications 
        WHERE product_id=%s
    """, (product_id,))
    product["specifications"] = {
        row["spec_key"]: row["spec_value"]
        for row in cursor.fetchall()
    }

    # ================= REVIEWS =================
    cursor.execute("""
        SELECT name, rating, comment 
        FROM product_reviews 
        WHERE product_id=%s
        ORDER BY id DESC
    """, (product_id,))
    product["reviews"] = cursor.fetchall()

    # ================= AVERAGE RATING =================
    cursor.execute("""
        SELECT 
            ROUND(AVG(rating),1) AS avg_rating,
            COUNT(rating) AS total_ratings
        FROM product_reviews
        WHERE product_id=%s
    """, (product_id,))

    rating_data = cursor.fetchone()

    product["avg_rating"] = rating_data["avg_rating"] or 0
    product["total_ratings"] = rating_data["total_ratings"] or 0

    # ================= RELATED PRODUCTS =================
    cursor.execute("""
        SELECT id, name, image, price 
        FROM products 
        WHERE category_id=%s AND id!=%s
        LIMIT 8
    """, (product["category_id"], product_id))
    related_products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "product_detail.html",
        product=product,
        similar_products=related_products
    )

@app.route("/rate-product", methods=["POST"])
def rate_product():
    if "user_id" not in session:
        return jsonify({"status": "login_required"})

    product_id = request.form.get("product_id")
    rating = request.form.get("rating")
    user_id = session["user_id"]

    conn = get_db()   # ✅ FIXED
    cursor = conn.cursor()

    # Check if already rated
    cursor.execute(
        "SELECT id FROM product_ratings WHERE product_id=%s AND user_id=%s",
        (product_id, user_id)
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE product_ratings SET rating=%s WHERE id=%s",
            (rating, existing[0])
        )
    else:
        cursor.execute(
            "INSERT INTO product_ratings (product_id,user_id,rating) VALUES (%s,%s,%s)",
            (product_id, user_id, rating)
        )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "success"})

@app.route("/add_review/<int:product_id>", methods=["POST"])
def add_review(product_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    rating = request.form["rating"]
    comment = request.form["comment"]
    user_id = session["user_id"]

    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO product_reviews (product_id, user_id, rating, comment)
        VALUES (%s, %s, %s, %s)
    """, (product_id, user_id, rating, comment))

    db.commit()

    return redirect(url_for("product_detail", product_id=product_id))


# ---------- CANCEL ORDER ----------
@app.route("/cancel_order/<int:order_id>")
def cancel_order(order_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE orders
        SET status='Cancelled'
        WHERE id=%s AND user_id=%s AND status='Pending'
    """, (order_id, session["user_id"]))

    conn.commit()
    cur.close()
    conn.close()

    flash("Order cancelled successfully!", "success")
    return redirect(url_for("orders"))

# ---------- INVOICE ----------
@app.route("/invoice/<int:order_id>")
def invoice(order_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT o.*, u.name, u.email
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = %s AND o.user_id = %s
    """, (order_id, session["user_id"]))

    order = cur.fetchone()

    cur.close()
    conn.close()

    if not order:
        return redirect(url_for("orders"))

    # calculations
    order["subtotal"] = order["price"] * order["quantity"]
    order["shipping"] = 0
    order["total"] = order["subtotal"] + order["shipping"]

    return render_template("invoice.html", order=order)

# ---------- PROFILE ----------
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])

    if request.method == "POST":
        name = request.form["name"]
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE users SET name=%s WHERE id=%s", (name, user["id"]))
        conn.commit()
        cur.close()
        conn.close()

        session["user_name"] = name
        flash("Profile updated", "success")
        return redirect(url_for("profile"))

    # --- Calculate years active & member since safely ---
    created_at = user.get("created_at")  # key from DB
    if created_at:
        if isinstance(created_at, str):
            created_at_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        else:
            created_at_dt = created_at
        member_since = created_at_dt.year
        years_active = datetime.now().year - member_since
    else:
        member_since = "N/A"
        years_active = 0

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template(
        "profile.html",
        user=user,
        member_since=member_since,
        years_active=years_active,
        current_time=current_time
    )

# ---------- SECURITY ----------
@app.route("/security", methods=["GET", "POST"])
def security():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Get current user
    cur.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    user = cur.fetchone()

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        # Check current password
        if not check_password_hash(user["password"], current_password):
            flash("Current password is incorrect!", "danger")
            return redirect(url_for("security"))

        # Check new password match
        if new_password != confirm_password:
            flash("New passwords do not match!", "danger")
            return redirect(url_for("security"))

        # Update password
        new_hashed_password = generate_password_hash(new_password)

        cur.execute("UPDATE users SET password=%s WHERE id=%s",
                    (new_hashed_password, session["user_id"]))
        conn.commit()

        flash("Password updated successfully!", "success")
        return redirect(url_for("security"))

    cur.close()
    conn.close()

    return render_template("security.html", user=user)

# ---------- CHECKOUT ----------
@app.route("/checkout")
def checkout():
    if "user_id" not in session:
        return redirect(url_for("login"))

    cart = session.get("cart", {})
    if not cart:
        flash("Your cart is empty", "warning")
        return redirect(url_for("all_categories"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    items = []
    total = 0
    for pid, qty in cart.items():
        cur.execute("SELECT * FROM products WHERE id=%s", (pid,))
        p = cur.fetchone()
        if p:
            p["qty"] = qty
            p["total"] = qty * p["price"]
            total += p["total"]
            items.append(p)

    cur.close()
    conn.close()

    return render_template("checkout.html", items=items, total=total)


@app.route("/place_order", methods=["POST"])
def place_order():

    # 🔐 Login check
    if "user_id" not in session:
        return redirect(url_for("login"))

    # 🛒 Cart check
    cart = session.get("cart", {})
    if not cart:
        flash("Cart is empty!", "warning")
        return redirect(url_for("checkout"))

    conn = get_db()
    cur = conn.cursor()

    for pid, qty in cart.items():

        # 🛍 Product fetch
        cur.execute("""
            SELECT id, name, price, image
            FROM products
            WHERE id=%s
        """, (pid,))
        p = cur.fetchone()

        if p:
            product_id, name, price, image = p

            total_price = price * qty   # ✅ correct total

            # 📝 Insert Order (STATUS = Pending)
            cur.execute("""
                INSERT INTO orders
                (user_id, product_id, product_name, product_image, quantity, price, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                session["user_id"],
                product_id,
                name,
                image,
                qty,
                total_price,
                "Pending"   # ✅ FIXED HERE
            ))

    conn.commit()
    cur.close()
    conn.close()

    # 🧹 Clear cart
    session.pop("cart")

    flash("Order placed successfully!", "success")
    return redirect(url_for("orders"))

@app.route("/clear_cart", methods=["POST"])
def clear_cart():
    session.pop("cart", None)
    return jsonify({"success": True})


@app.route("/view_order/<int:order_id>")
def view_order(order_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    # Add buffered=True
    cur = conn.cursor(dictionary=True, buffered=True)

    try:
        cur.execute("""
            SELECT o.id, o.user_id, o.product_name, o.quantity, o.price, o.status, o.created_at,
                   p.image AS product_image
            FROM orders o
            LEFT JOIN products p ON o.product_name = p.name
            WHERE o.id = %s AND o.user_id = %s
        """, (order_id, session["user_id"]))

        order = cur.fetchone()  # Fetch the result **immediately**

        if not order:
            flash("Order not found!", "danger")
            return redirect(url_for("orders"))

    finally:
        cur.close()  # Safe to close now
        conn.close()

    return render_template("order_detail.html", order=order)


@app.route("/addresses")
def addresses():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Get user details
    cur.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    user = cur.fetchone()

    # Get user addresses
    cur.execute("SELECT * FROM addresses WHERE user_id=%s", (session["user_id"],))
    address_list = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("addresses.html", 
                           addresses=address_list,
                           user=user)   # 👈 VERY IMPORTANT


@app.route("/add_address", methods=["GET", "POST"])
def add_address():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Get user for left panel
    cur.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    user = cur.fetchone()

    if request.method == "POST":
        fullname = request.form["fullname"]
        phone = request.form["phone"]
        address = request.form["address"]
        city = request.form["city"]
        pincode = request.form["pincode"]

        cur.execute("""
            INSERT INTO addresses (user_id, fullname, phone, address, city, pincode)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            session["user_id"],
            fullname,
            phone,
            address,
            city,
            pincode
        ))

        conn.commit()
        cur.close()
        conn.close()

        flash("Address Added Successfully!", "success")
        return redirect(url_for("addresses"))

    cur.close()
    conn.close()
    return render_template("add_address.html", user=user)


@app.route("/delete_address/<int:id>", methods=["POST"])
def delete_address(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()  # ✅ use get_db(), not get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM addresses WHERE id=%s AND user_id=%s",
                (id, session["user_id"]))
    conn.commit()

    cur.close()
    conn.close()

    flash("Address deleted successfully!", "success")
    return redirect(url_for("addresses"))

@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Stats
    cur.execute("SELECT COUNT(*) AS total_users FROM users")
    total_users = cur.fetchone()["total_users"]

    cur.execute("SELECT COUNT(*) AS total_orders FROM orders")
    total_orders = cur.fetchone()["total_orders"]

    cur.execute("SELECT COUNT(*) AS total_products FROM products")
    total_products = cur.fetchone()["total_products"]

    cur.execute("SELECT IFNULL(SUM(price),0) AS total_revenue FROM orders")
    total_revenue = cur.fetchone()["total_revenue"]

    # Users list
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()

    # Orders list with user names
    cur.execute("""
        SELECT o.*, u.name AS user_name
        FROM orders o
        JOIN users u ON o.user_id = u.id
    """)
    orders = cur.fetchall()

    # Products list with category names
    cur.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
    """)
    products = cur.fetchall()

    # Categories list with product count
    cur.execute("""
        SELECT c.*, COUNT(p.id) AS products_count
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id
        GROUP BY c.id
    """)
    categories = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_orders=total_orders,
        total_products=total_products,
        total_revenue=total_revenue,
        users=users,
        orders=orders,
        products=products,
        categories=categories
    )


@app.route("/admin/users")
def admin_users():
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("admin_users.html", users=users)



@app.route("/admin/orders")
def admin_orders():
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT o.*, u.name AS user_name
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
    """)
    orders = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("admin_orders.html", orders=orders)


@app.route("/admin/categories")
def admin_categories():
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT c.*, COUNT(p.id) AS products_count
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id
        GROUP BY c.id
    """)
    categories = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("admin_categories.html", categories=categories)


@app.route("/admin/reviews")
def admin_reviews():
    if "user_role" not in session or session["user_role"] != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT r.*, p.name AS product_name
        FROM reviews r
        JOIN products p ON r.product_id = p.id
        ORDER BY r.created_at DESC
    """)
    reviews = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin_reviews.html", reviews=reviews)


@app.route("/admin/profile", methods=["GET", "POST"])
def admin_profile():
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    admin = cur.fetchone()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        cur.execute("UPDATE users SET name=%s, email=%s WHERE id=%s", (name, email, admin["id"]))
        conn.commit()
        session["user_name"] = name
        flash("Profile updated successfully!", "success")
        return redirect(url_for("admin_profile"))

    cur.close()
    conn.close()
    return render_template("admin_profile.html", admin=admin)


@app.route("/admin/products")
def admin_products():
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
    """)
    products = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("admin_products.html", products=products)


# ---------- EDIT USER ----------
@app.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Fetch user data
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    if not user:
        flash("User not found", "danger")
        return redirect(url_for("admin_users"))

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        role = request.form["role"]

        cur.execute(
            "UPDATE users SET name=%s, email=%s, role=%s WHERE id=%s",
            (name, email, role, user_id)
        )
        conn.commit()
        flash("User updated successfully", "success")
        return redirect(url_for("admin_users"))

    cur.close()
    conn.close()
    return render_template("admin_edit_user.html", user=user)


# ---------- DELETE USER ----------
@app.route("/admin/users/delete/<int:user_id>")
def delete_user(user_id):
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    # Optional: prevent deleting admin
    cur.execute("SELECT role FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    if user and user[0] == "admin":
        flash("Cannot delete admin user!", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("admin_users"))

    # Delete the user
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("User deleted successfully!", "success")
    return redirect(url_for("admin_users"))


# ---------- UPDATE ORDER STATUS ----------
@app.route("/admin/orders/update/<int:order_id>", methods=["GET", "POST"])
def update_order_status(order_id):
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        new_status = request.form.get("status")  # status sent from a form
        cur.execute("UPDATE orders SET status=%s WHERE id=%s", (new_status, order_id))
        conn.commit()
        flash("Order status updated!", "success")
        cur.close()
        conn.close()
        return redirect(url_for("admin_orders"))

    # For GET request: fetch current order
    cur.execute("SELECT id, status FROM orders WHERE id=%s", (order_id,))
    order = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("update_order_status.html", order=order)


@app.route("/admin/orders/invoice/<int:order_id>")
def view_invoice(order_id):
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
    order = cur.fetchone()
    cur.close()
    conn.close()

    return render_template("invoice.html", order=order)


# Route to Add Product
@app.route("/admin/products/add", methods=["GET", "POST"])
def add_product():
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        category_id = request.form["category_id"]

        cursor.execute(
            "INSERT INTO products (name, price, category_id) VALUES (%s, %s, %s)",
            (name, price, category_id)
        )
        conn.commit()

        flash("Product added successfully!", "success")
        cursor.close()
        conn.close()
        return redirect(url_for("admin_products"))

    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("add_product.html", categories=categories)


# Route to Edit Product
@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch product
    cursor.execute("SELECT * FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        return redirect(url_for("admin_products"))

    # Fetch categories
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        category_id = request.form.get("category_id")

        cursor.execute("""
            UPDATE products 
            SET name=%s, price=%s, category_id=%s 
            WHERE id=%s
        """, (name, price, category_id, product_id))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Product updated successfully!", "success")
        return redirect(url_for("admin_products"))

    cursor.close()
    conn.close()
    return render_template(
        "edit_product.html",
        product=product,
        categories=categories
    )


# Route to Delete Product
@app.route("/admin/products/delete/<int:product_id>", methods=["POST", "GET"])
def delete_product(product_id):
    # Check admin
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    # Connect to DB
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Get the product to delete (to remove image)
    cursor.execute("SELECT image FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("admin_products"))

    # 2️⃣ Remove the image file if it exists
    if product['image']:
        image_path = os.path.join("static/images", product['image'])
        if os.path.exists(image_path):
            os.remove(image_path)

    # 3️⃣ Delete product from database
    cursor.execute("DELETE FROM products WHERE id=%s", (product_id,))
    conn.commit()

    # 4️⃣ Close DB connection
    cursor.close()
    conn.close()

    flash("Product deleted successfully!", "success")
    return redirect(url_for("admin_products"))


# Route to Add Category
@app.route("/admin/categories/add", methods=["GET", "POST"])
def add_category():
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name").strip()

        # Connect to DB
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Check if category already exists
        cursor.execute("SELECT * FROM categories WHERE name=%s", (name,))
        existing = cursor.fetchone()
        if existing:
            flash("Category already exists!", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for("admin_categories"))

        # Insert new category
        cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
        conn.commit()

        cursor.close()
        conn.close()

        flash("Category added successfully!", "success")
        return redirect(url_for("admin_categories"))

    return render_template("add_category.html")

# Route to Edit Category
@app.route("/admin/categories/edit/<int:category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch the category
    cursor.execute("SELECT * FROM categories WHERE id=%s", (category_id,))
    category = cursor.fetchone()

    if not category:
        flash("Category not found!", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("admin_categories"))

    if request.method == "POST":
        new_name = request.form.get("name")

        # Check if new name already exists
        cursor.execute("SELECT * FROM categories WHERE name=%s AND id != %s", (new_name, category_id))
        existing = cursor.fetchone()
        if existing:
            flash("Category name already exists!", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for("admin_categories"))

        # Update category
        cursor.execute("UPDATE categories SET name=%s WHERE id=%s", (new_name, category_id))
        conn.commit()  # commit using the connection, not mysql.connection
        flash("Category updated successfully!", "success")
        cursor.close()
        conn.close()
        return redirect(url_for("admin_categories"))

    cursor.close()
    conn.close()
    return render_template("edit_category.html", category=category)

# Route to delete category
@app.route("/admin/categories/delete/<int:category_id>")
def delete_category(category_id):
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access only!", "danger")
        return redirect(url_for("login"))

    # Connect to database
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Check if category exists
    cursor.execute("SELECT * FROM categories WHERE id=%s", (category_id,))
    category = cursor.fetchone()
    if not category:
        flash("Category not found!", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("admin_categories"))

    # Optional: Check if any products exist in this category
    cursor.execute("SELECT COUNT(*) AS product_count FROM products WHERE category_id=%s", (category_id,))
    count = cursor.fetchone()["product_count"]
    if count > 0:
        flash("Cannot delete category with products!", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("admin_categories"))

    # Delete category
    cursor.execute("DELETE FROM categories WHERE id=%s", (category_id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Category deleted successfully!", "success")
    return redirect(url_for("admin_categories"))

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "success")
    return redirect(url_for("login"))

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
