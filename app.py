from flask import Flask, render_template, request, redirect, session, flash
import os, random, datetime
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import hashlib
import uuid
import requests
from flask_migrate import Migrate
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
load_dotenv()
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from flask import send_file
import io
import resend
app = Flask(__name__)

app.secret_key = "secret123"
PAYU_KEY = "BGGPVO"
PAYU_SALT = "Oh9axP7ltLTylwzSf7EU4iDQ4U2gxbT"
PAYU_URL = "https://secure.payu.in/_payment"

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)
db = SQLAlchemy(app)

migrate = Migrate(app, db)

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

    search = request.args.get("search")

    if search:

        products = Product.query.filter(
            Product.name.ilike(f"%{search}%")
        ).all()

    else:

        products = Product.query.all()

    return render_template(
    "home.html",
    products=products,
    search=search
)

@app.route("/add-to-cart/<int:id>")
def add_to_cart(id):

    product = Product.query.get_or_404(id)

    customer_name = session.get("customer_name", "Guest Customer")

    cart_item = Cart.query.filter_by(
        customer_name=customer_name,
        product_id=id
    ).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = Cart(
            customer_name=customer_name,
            product_id=id,
            quantity=1
        )
        db.session.add(cart_item)

    db.session.commit()

    flash("Product added to cart!")

    return redirect("/")

@app.route("/cart")
def cart():

    customer_name = session.get("customer_name", "Guest Customer")

    cart_items = Cart.query.filter_by(
        customer_name=customer_name
    ).all()

    products = []

    total = 0

    for item in cart_items:

        product = Product.query.get(item.product_id)

        if product:

            subtotal = product.price * item.quantity

            total += subtotal

            products.append({
                "id": item.id,
                "name": product.name,
                "image": product.image,
                "price": product.price,
                "quantity": item.quantity,
                "subtotal": subtotal
            })

    return render_template(
        "cart.html",
        products=products,
        total=total
    )

@app.route("/cart/increase/<int:id>")
def increase_cart(id):

    item = Cart.query.get_or_404(id)

    item.quantity += 1

    db.session.commit()

    return redirect("/cart")

@app.route("/cart/decrease/<int:id>")
def decrease_cart(id):

    item = Cart.query.get_or_404(id)

    if item.quantity > 1:
        item.quantity -= 1
    else:
        db.session.delete(item)

    db.session.commit()

    return redirect("/cart")

@app.route("/cart/delete/<int:id>")
def delete_cart(id):

    item = Cart.query.get_or_404(id)

    db.session.delete(item)

    db.session.commit()

    return redirect("/cart")

@app.route("/checkout-cart")
def checkout_cart():

    customer_name = session.get("customer_name", "Guest Customer")

    cart_items = Cart.query.filter_by(
        customer_name=customer_name
    ).all()

    if not cart_items:
        flash("Your cart is empty!")
        return redirect("/cart")

    total = 0

    for item in cart_items:

        product = Product.query.get(item.product_id)

        if product:
            total += product.price * item.quantity

    session["cart_total"] = total
    session["product_name"] = "BESTTIVE-CART"

    session["amount"] = str(total)

    return redirect("/payment/BESTTIVE-CART/" + str(total))

# 🔥 PAYMENT PAGE
@app.route("/payment/<string:name>/<int:price>")
def payment(name, price):
    return render_template("payment.html", name=name, price=price)

@app.route("/payu-payment", methods=["POST"])
def payu_payment():

    # Login required
    if not session.get("user_id"):
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user:
        session.clear()
        return redirect("/login")

    product_name = request.form["product_name"]
    amount = request.form["amount"]

    # Find product
    product = Product.query.filter_by(
        name=product_name
    ).first()

    if not product:
        flash("Product not found!")
        return redirect("/")

    # Save order information temporarily
    session["product_name"] = product.name
    session["product_id"] = product.id
    session["amount"] = amount
    session["customer_name"] = user.name
    session["customer_email"] = user.email
    session["customer_phone"] = user.phone
    session["customer_address"] = user.address

    txnid = str(uuid.uuid4())[:20]

    firstname = user.name or "BESTTIVE Customer"
    email = user.email
    phone = user.phone or "9999999999"

    success_url = request.url_root + "payment-success"
    failure_url = request.url_root + "payment-failure"

    hash_string = (
        f"{PAYU_KEY}|{txnid}|{amount}|{product.name}|"
        f"{firstname}|{email}|||||||||||{PAYU_SALT}"
    )

    hashh = hashlib.sha512(
        hash_string.encode()
    ).hexdigest()

    return render_template(
        "payu_redirect.html",
        payu_url=PAYU_URL,
        key=PAYU_KEY,
        txnid=txnid,
        amount=amount,
        productinfo=product.name,
        firstname=firstname,
        email=email,
        phone=phone,
        surl=success_url,
        furl=failure_url,
        hash=hashh
    )
@app.route("/qr-payment-success", methods=["POST"])
def qr_payment_success():

    # Login required
    if not session.get("user_id"):
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user:
        session.clear()
        return redirect("/login")

    product_name = request.form.get("product_name")
    amount = request.form.get("amount")

    product = Product.query.filter_by(
        name=product_name
    ).first()

    if not product:
        flash("Product not found.")
        return redirect("/")

    new_order = Order(
        user_id=user.id,
        product_id=product.id,
        quantity=1,
        price=product.price,
        total_amount=int(amount),
        address=user.address or "",
        status="Payment Verification"
    )

    db.session.add(new_order)
    db.session.commit()

    return render_template(
        "payment_success.html",
        customer_name=user.name,
        product_name=product.name,
        amount=amount,
        status="Payment Verification"
    )

@app.route("/payment-success", methods=["POST"])
def payment_success():

    # Login check
    if not session.get("user_id"):
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user:
        session.clear()
        return redirect("/login")

    customer_name = user.name
    product_name = session.get("product_name")
    amount = session.get("amount")

    if not product_name:
        flash("Order information not found.")
        return redirect("/")

    # CART ORDER
    if product_name == "BESTTIVE Shopping Cart":

        cart_items = Cart.query.filter_by(
            customer_name=customer_name
        ).all()

        total_amount = 0

        for item in cart_items:

            product = Product.query.get(item.product_id)

            if product:

                item_total = product.price * item.quantity

                new_order = Order(
                    user_id=user.id,
                    product_id=product.id,
                    quantity=item.quantity,
                    price=product.price,
                    total_amount=item_total,
                    address=user.address or "",
                    status="Pending"
                )

                db.session.add(new_order)

                total_amount += item_total

                db.session.delete(item)

        db.session.commit()

        return render_template(
            "payment_success.html",
            customer_name=customer_name,
            product_name="BESTTIVE Shopping Cart",
            amount=total_amount,
            status="Pending"
        )

    # SINGLE PRODUCT ORDER

    product_id = session.get("product_id")
    product = Product.query.get(product_id)

    if not product:

        flash("Product not found.")
        return redirect("/")

    new_order = Order(
        user_id=user.id,
        product_id=product.id,
        quantity=1,
        price=product.price,
        total_amount=int(amount),
        address=user.address or "",
        status="Pending"
    )

    db.session.add(new_order)

    db.session.commit()

    return render_template(
        "payment_success.html",
        customer_name=customer_name,
        product_name=product.name,
        amount=amount,
        status="Pending"
    )

@app.route("/payment-failure", methods=["POST"])
def payment_failure():

    flash("Payment Failed!")

    return redirect("/")

# 🔥 ADD TO CART

@app.route("/payment", methods=["GET", "POST"])
def payment_form():
    if request.method == "POST":
        name = request.form["name"]
        amount = request.form["amount"]
        return f"Payment Successful! {name} paid ₹{amount}"
    return render_template("payment.html")

from flask_mail import Mail, Message

app.config['SECRET_KEY'] = "CHANGE_THIS_SECRET_KEY"

@app.route("/product/<int:id>")
def product_details(id):

    product = Product.query.get_or_404(id)

    images = ProductImage.query.filter_by(
        product_id=product.id
    ).all()

    return render_template(
        "product_details.html",
        product=product,
        images=images
    )

# DB (SQLite)

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
    phone = db.Column(db.String(20), default="")
    address = db.Column(db.String(255), default="")
    dob = db.Column(db.String(50), default="")
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    stock = db.Column(db.Integer, default=0)
    
class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    image = db.Column(db.String(500), nullable=False)

    product = db.relationship(
        "Product",
        backref=db.backref("images", lazy=True)
    )

class Wishlist(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    user = db.relationship(
        "User",
        backref="wishlist"
    )

    product = db.relationship("Product")

class Order(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        default=1
    )

    price = db.Column(
        db.Integer,
        nullable=False
    )

    total_amount = db.Column(
        db.Integer,
        nullable=False
    )

    address = db.Column(
        db.String(255),
        default=""
    )

    status = db.Column(
        db.String(50),
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow
    )

    user = db.relationship("User")
    product = db.relationship("Product")

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    customer_name = db.Column(db.String(100), nullable=False)

    product_id = db.Column(db.Integer, nullable=False)

    quantity = db.Column(db.Integer, default=1)

    created_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow
    )
    
# --------- HELPERS ---------

def send_otp(email, otp):

    try:

        resend.api_key = os.environ.get("RESEND_API_KEY")

        resend.Emails.send({
            "from": "BESTTIVE <onboarding@resend.dev>",
            "to": [email],
            "subject": "BESTTIVE Login OTP",
            "text": f"Your BESTTIVE Login OTP is: {otp}"
        })

        print("OTP MAIL SENT")

    except Exception as e:

        print("MAIL ERROR:", e)

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

            user = User.query.filter_by(email=email).first()

            if not user:
                user = User(email=email)
                db.session.add(user)
                db.session.commit()

            session["user_id"] = user.id

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

    total_products = Product.query.count()

    return render_template(
        "admin_dashboard.html",
        total_products=total_products
    )

@app.route("/admin/add-product", methods=["GET", "POST"])
def admin_add_product():

    # Admin login check
    if not session.get("admin"):
        return redirect("/admin")

    if request.method == "POST":

        name = request.form.get("name")
        price = request.form.get("price")
        description = request.form.get("description")
        stock = request.form.get("stock")

        # Main Image
        image = request.files["image"]

        upload_result = cloudinary.uploader.upload(image)
        image_url = upload_result["secure_url"]

        new_product = Product(
            name=name,
            price=int(price),
            image=image_url,
            description=description,
            stock=int(stock)
        )

        db.session.add(new_product)
        db.session.commit()

        # Extra Images
        extra_images = [
            request.files.get("image2"),
            request.files.get("image3"),
            request.files.get("image4"),
            request.files.get("image5")
        ]

        for img in extra_images:

            if img and img.filename != "":

                upload = cloudinary.uploader.upload(img)

                product_image = ProductImage(
                    product_id=new_product.id,
                    image=upload["secure_url"]
                )

                db.session.add(product_image)

        db.session.commit()

        flash("Product Added Successfully!")
        return redirect("/admin/dashboard")

    return render_template("add_product.html")

@app.route("/admin/products")
def manage_products():

    if not session.get("admin"):
        return redirect("/admin")

    products = Product.query.all()

    return render_template(
        "manage_products.html",
        products=products
    )

@app.route("/admin/delete-product/<int:id>")
def delete_product(id):

    if not session.get("admin"):
        return redirect("/admin")

    product = Product.query.get_or_404(id)

    # Delete all extra images
    ProductImage.query.filter_by(product_id=id).delete()

    # Delete main product
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

            upload_result = cloudinary.uploader.upload(image)

            product.image = upload_result["secure_url"]

        db.session.commit()
        flash("Product Updated Successfully")
        return redirect("/admin/products")

    return render_template("edit_product.html", product=product)

@app.route("/admin/orders")
def admin_orders():

    if not session.get("admin"):
        return redirect("/admin")

    orders = Order.query.order_by(Order.id.desc()).all()

    return render_template(
        "admin_orders.html",
        orders=orders
    )

@app.route("/admin/update-order-status/<int:id>", methods=["POST"])
def update_order_status(id):

    if not session.get("admin"):
        return redirect("/admin")

    order = Order.query.get_or_404(id)

    order.status = request.form["status"]

    db.session.commit()

    flash("Order Status Updated Successfully!")

    return redirect("/admin/orders")

@app.route("/admin/customers")
def admin_customers():

    if not session.get("admin"):
        return redirect("/admin")

    customers = User.query.all()

    return render_template(
        "admin_customers.html",
        customers=customers
    )

@app.route("/admin/delete-customers", methods=["POST"])
def delete_customers():

    if not session.get("admin"):
        return redirect("/admin")

    customer_ids = request.form.getlist("customer_ids")

    if not customer_ids:
        flash("Please select at least one customer.")
        return redirect("/admin/customers")

    for customer_id in customer_ids:

        customer = User.query.get(int(customer_id))

        if customer:

            # Delete customer's wishlist first
            Wishlist.query.filter_by(
                user_id=customer.id
            ).delete()

            # Then delete customer
            db.session.delete(customer)

    db.session.commit()

    flash("Selected customers removed successfully!")

    return redirect("/admin/customers")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/orders")
def orders():

    if not session.get("user_id"):
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user:
        session.clear()
        return redirect("/login")

    orders = (
        Order.query
        .filter_by(user_id=user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return render_template(
        "orders.html",
        orders=orders
    )

@app.route("/invoice/<int:id>")
def invoice(id):

    order = Order.query.get_or_404(id)

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("<b>BESTTIVE</b>", styles["Title"]))
    story.append(Paragraph("Invoice", styles["Heading2"]))
    story.append(Paragraph("<hr/>", styles["Normal"]))
    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph(f"Customer : {order.customer_name}", styles["Normal"]))
    story.append(Paragraph(f"Product : {order.product_name}", styles["Normal"]))
    story.append(Paragraph(f"Amount : ₹{order.amount}", styles["Normal"]))
    story.append(Paragraph(f"Status : {order.status}", styles["Normal"]))
    story.append(Paragraph(f"Date : {order.created_at.strftime('%d-%m-%Y %H:%M')}", styles["Normal"]))

    story.append(Paragraph("<br/><br/>", styles["Normal"]))
    story.append(Paragraph("Thank you for shopping with BESTTIVE ❤️", styles["Heading3"]))

    doc.build(story)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"BESTTIVE_Invoice_{order.id}.pdf",
        mimetype="application/pdf"
    )


@app.route("/wishlist/add/<int:product_id>")
def add_to_wishlist(product_id):

    if not session.get("user_id"):
        return redirect("/login")

    user_id = session["user_id"]

    # Check that logged-in user still exists
    user = User.query.get(user_id)

    if not user:
        session.clear()
        return redirect("/login")

    product = Product.query.get_or_404(product_id)

    existing = Wishlist.query.filter_by(
        user_id=user_id,
        product_id=product.id
    ).first()

    if not existing:

        item = Wishlist(
            user_id=user_id,
            product_id=product.id
        )

        db.session.add(item)
        db.session.commit()

        flash("Added to Wishlist ❤️")

    else:

        flash("Product already in Wishlist ❤️")

    return redirect(request.referrer or "/")

@app.route("/wishlist/remove/<int:item_id>")
def remove_from_wishlist(item_id):

    if not session.get("user_id"):
        return redirect("/login")

    item = Wishlist.query.filter_by(
        id=item_id,
        user_id=session["user_id"]
    ).first_or_404()

    db.session.delete(item)
    db.session.commit()

    flash("Removed from Wishlist")

    return redirect("/wishlist")

@app.route("/wishlist")
def wishlist():

    if not session.get("user_id"):
        return redirect("/login")

    items = Wishlist.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(
        "wishlist.html",
        items=items
    )

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
        user.phone = request.form.get("phone")
        user.dob = request.form.get("dob")
        db.session.commit()
        return redirect("/profile")

    return render_template("profile.html", user=user)
if __name__ == "__main__":
    app.run(debug=False)