from flask import Flask, render_template, request, redirect, session, flash
import os, random, datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
app = Flask(__name__)

app.secret_key = "secret123"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///besttive.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# PRODUCTS DATA
products = [
    {
        "name": "Bangles Set",
        "price": 299,
        "image": "images/bangles.jpg"
    }
]

# 🔥 HOME PAGE (ONLY ONCE)
@app.route("/")
def home():
    products = Product.query.all()
    return render_template("home.html", products=products)

# 🔥 PAYMENT PAGE
@app.route("/payment/<string:name>/<int:price>")
def payment(name, price):
    return render_template("payment.html", name=name, price=price)

# 🔥 ADD TO CART
@app.route("/add_to_cart/<name>/<int:price>")
def add_to_cart(name, price):
    cart.append({"name": name, "price": price})
    return redirect("/cart")

# 🔥 RUN APP (ONLY ONCE)
@app.route("/cart")
def view_cart():
    total = sum(item["price"] for item in cart)
    return render_template("cart.html", cart=cart, total=total)

@app.route("/payment", methods=["GET", "POST"])
def payment_form():
    if request.method == "POST":
        name = request.form["name"]
        amount = request.form["amount"]
        return f"Payment Successful! {name} paid ₹{amount}"
    return render_template("payment.html")

from flask_mail import Mail, Message

app.config['SECRET_KEY'] = "CHANGE_THIS_SECRET_KEY"

# DB (SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# MAIL CONFIG (Gmail SMTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "amitjia2000@gmail.com"
app.config['MAIL_PASSWORD'] = "qqcvybwavghvijgp"
mail = Mail(app)

# ----------- MODEL -----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), default="New User")
    address = db.Column(db.String(255), default="")
    dob = db.Column(db.String(50), default="")

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    stock = db.Column(db.Integer, default=0)

# Database create
with app.app_context():
    db.create_all()

# --------- HELPERS ---------
def send_otp(email, otp):

    try:

        msg = Message(
            subject="BESTTIVE Login OTP",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email],
            body=f"Your OTP is: {otp}"
        )

        mail.send(msg)

        print("MAIL SENT")

    except Exception as e:

        print("MAIL ERROR:", e)
# --------- ROUTES ---------

# Home (yahan tumhara existing home render kar sakte ho)

# LOGIN PAGE
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get("email")

        # generate OTP
        otp = random.randint(1000, 9999)

        session["otp"] = str(otp)
        session["email"] = email

        send_otp(email, otp)
        return redirect("/verify")

    return render_template("login.html")

# VERIFY OTP
@app.route("/verify", methods=["GET", "POST"])
def verify():

    if request.method == "POST":

        user_otp = request.form.get("otp")

        if user_otp == session.get("otp"):

            email = session.get("email")

            existing_user = User.query.filter_by(email=email).first()

    if existing_user:
      session["user_id"] = existing_user.id
      return redirect("/profile")
            
    flash("Wrong OTP")

    return render_template("verify.html")

# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = session.get("email")

        new_user = User(
            email=email,
            name=name
        )

        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        return redirect("/profile")

    return render_template("register.html")

@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "besttive123":
            session["admin"] = True
            return redirect("/admin/dashboard")

        flash("Invalid Login")

    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get("admin"):
        return redirect("/admin")

    return render_template("admin_dashboard.html")

@app.route("/admin/add-product", methods=["GET", "POST"])
def add_product():

    # Admin login check
    if not session.get("admin"):
        return redirect("/admin")

    if request.method == "POST":

        name = request.form.get("name")
        price = request.form.get("price")
        description = request.form.get("description")
        stock = request.form.get("stock")

        image = request.files["image"]

        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        new_product = Product(
            name=name,
            price=int(price),
            image="uploads/" + filename,
            description=description,
            stock=int(stock)
        )

        db.session.add(new_product)
        db.session.commit()

        flash("Product Added Successfully!")
        return redirect("/admin/dashboard")

    return render_template("add_product.html")

@app.route("/admin/products")
def manage_products():

    if not session.get("admin"):
        return redirect("/admin")

    products = Product.query.all()

    return render_template("manage_products.html", products=products)

@app.route("/admin/delete-product/<int:id>")
def delete_product(id):

    if not session.get("admin"):
        return redirect("/admin")

    product = Product.query.get_or_404(id)

    image_path = os.path.join("static", product.image)

    if os.path.exists(image_path):
        os.remove(image_path)

    db.session.delete(product)
    db.session.commit()

    flash("Product Deleted Successfully!")

    return redirect("/admin/products")

@app.route("/admin/edit-product/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    if not session.get("admin"):
        return redirect("/admin")

    product = Product.query.get_or_404(id)

    if request.method == "POST":

        product.name = request.form["name"]
        product.price = int(request.form["price"])
        product.description = request.form["description"]
        product.stock = int(request.form["stock"])

        image = request.files.get("image")

        if image and image.filename != "":
            filename = image.filename

            image.save(
                os.path.join(app.config["UPLOAD_FOLDER"], filename)
            )

            product.image = filename

        db.session.commit()

        flash("Product Updated Successfully")

        return redirect("/admin/products")

    return render_template("edit_product.html", product=product)

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/orders")
def orders():
    return "<h2>Your Orders</h2>"

@app.route("/wishlist")
def wishlist():
    return "<h2>Your Wishlist</h2>"

@app.route("/notifications")
def notifications():
    return "<h2>Notifications</h2>"

@app.route("/support")
def support():
    return "<h2>Customer Care</h2>"

@app.route("/download")
def download():
    return "<h2>Download App</h2>"

@app.route("/profile", methods=["GET", "POST"])
def profile():
    uid = session.get("user_id")
    if not uid:
        return redirect("/login")

    user = User.query.get(uid)
    if not user:
        return redirect("/login")

    if request.method == "POST":
        user.name = request.form.get("name")
        user.address = request.form.get("address")
        user.dob = request.form.get("dob")
        db.session.commit()
        return redirect("/profile")

    return render_template("profile.html", user=user)
if __name__ == "__main__":
    app.run(debug=False)