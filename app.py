from flask import Flask, render_template, request, redirect, session, flash
import os, random, datetime
app = Flask(__name__)
app.secret_key = "secret123"  # required for session
# 🔥 CART LIST
cart = []
users = {}

# PRODUCTS DATA
products = [
    {"name": "Bangles Set", "price": 299, "image": "images/bangles.jpg"},
    {"name": "Mobile Phone", "price": 12999, "image": "images/mobile.jpg"},
    {"name": "Toys", "price": 399, "image": "images/toy.jpg"},
]

# 🔥 HOME PAGE (ONLY ONCE)
@app.route("/")
def home():
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

from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message

app.config['SECRET_KEY'] = "CHANGE_THIS_SECRET_KEY"

# DB (SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# MAIL CONFIG (Gmail SMTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "amitjia2000@gmail.com"
app.config['MAIL_PASSWORD'] = "qqcvybwavghvijgp"
mail = Mail(app)

# --------- MODEL ---------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), default="New User")
    address = db.Column(db.String(255), default="")
    dob = db.Column(db.String(50), default="")

with app.app_context():
    db.create_all()

# --------- HELPERS ---------
# --------- HELPERS ---------
def send_otp(email, otp):

    print("OTP:", otp)
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

        print("OTP:", otp)
        return redirect("/verify")

    return render_template("login.html")

# VERIFY OTP
@app.route("/verify", methods=["GET", "POST"])
def verify():

    if request.method == "POST":

        user_otp = request.form.get("otp")

        if user_otp == session.get("otp"):

            email = session.get("email")

            # existing user
            if email in users:
                session["user"] = users[email]
                return redirect("/profile")

            return redirect("/register")

        flash("Wrong OTP")

    return render_template("verify.html")

# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        phone = session.get("phone")

        users[phone] = {"name": name, "phone": phone}
        session["user"] = users[phone]

        return redirect("/profile")

    return render_template("register.html")

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