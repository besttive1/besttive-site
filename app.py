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
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from flask import send_file
import io
from flask import send_file
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
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

pdfmetrics.registerFont(
    TTFont(
        "DejaVuSans",
        os.path.join(BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
    )
)

pdfmetrics.registerFont(
    TTFont(
        "DejaVuSans-Bold",
        os.path.join(BASE_DIR, "static", "fonts", "DejaVuSans-Bold.ttf")
    )
)

# ================= SHIPROCKET API =================

def get_shiprocket_token():
    try:
        url = "https://apiv2.shiprocket.in/v1/external/auth/login"

        payload = {
            "email": os.getenv("SHIPROCKET_EMAIL"),
            "password": os.getenv("SHIPROCKET_PASSWORD")
        }

        response = requests.post(url, json=payload)
        data = response.json()

        if response.status_code == 200 and "token" in data:
            return data["token"]

        print("Shiprocket Login Error:", data)
        return None

    except Exception as e:
        print("Shiprocket Error:", e)
        return None

@app.route("/test-shiprocket")
def test_shiprocket():
    token = get_shiprocket_token()

    if token:
        return "Shiprocket Connected Successfully!"
    else:
        return "Shiprocket Connection Failed. Check terminal."


# 🔥 HOME PAGE (ONLY ONCE)
@app.route("/")
def home():

    search = request.args.get("search")
    category = request.args.get("category")
    subcategory = request.args.get("subcategory")
    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    sort = request.args.get("sort")
    query = Product.query

    banners = Banner.query.filter_by(
        active=True
    ).order_by(
        Banner.position.asc()
    ).all()

    # Search
    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%")
        )

    # Category filter
    if category:
        query = query.filter(
            Product.category == category
        )

    # Subcategory filter
    if subcategory:
        query = query.filter(
            Product.subcategory == subcategory
        )

    # Price filter
    if min_price is not None:
       query = query.filter(
           Product.price >= min_price
        )

    if max_price is not None:
       query = query.filter(
           Product.price <= max_price
        )

    # Sorting
    if sort == "low":
       query = query.order_by(
           Product.price.asc()
            )

    elif sort == "high":
       query = query.order_by(
           Product.price.desc()
        )

    elif sort == "newest":
       query = query.order_by(
           Product.id.desc()
        )

    products = query.all()
    
    # Get subcategories automatically from database
    subcategories = []

    if category:
        subcategories = (
            db.session.query(Product.subcategory)
            .filter(
                Product.category == category,
                Product.subcategory.isnot(None),
                Product.subcategory != ""
            )
            .distinct()
            .all()

        )
        subcategories = [item[0] for item in subcategories]

    wishlist_product_ids = []
    
    if session.get("user_id"):
            wishlist_product_ids = [
              item.product_id
              for item in Wishlist.query.filter_by(
                  user_id=session["user_id"]
              ).all()
            ]
    return render_template(
        "home.html",
        products=products,
        search=search,
        category=category,
        subcategory=subcategory,
        subcategories=subcategories,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        banners=banners,
        wishlist_product_ids=wishlist_product_ids
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

    product = Product.query.filter_by(
        name=name
    ).first_or_404()

    tax = calculate_tax(product, 1)

    return render_template(
        "payment.html",
        name=product.name,
        price=product.price,
        taxable_amount=tax["taxable_amount"],
        gst_rate=tax["gst_rate"],
        gst_amount=tax["gst_amount"],
        final_amount=tax["total_amount"]
    )

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

    # Find product
    product = Product.query.filter_by(
        name=product_name
    ).first()

    if not product:
        flash("Product not found!")
        return redirect("/")

    # Automatic GST calculation
    tax = calculate_tax(product, 1)

    taxable_amount = tax["taxable_amount"]
    gst_rate = tax["gst_rate"]
    gst_amount = tax["gst_amount"]
    final_amount = tax["total_amount"]

    # Final amount including GST
    amount = str(final_amount)

    # Save order/payment information temporarily
    session["product_name"] = product.name
    session["product_id"] = product.id
    session["amount"] = amount

    # Save tax information for payment success
    session["taxable_amount"] = taxable_amount
    session["gst_rate"] = gst_rate
    session["gst_amount"] = gst_amount
    session["hsn_code"] = product.hsn_code or ""

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

    product = Product.query.filter_by(
        name=product_name
    ).first()

    if not product:
        flash("Product not found.")
        return redirect("/")

    # =========================
    # STOCK AVAILABILITY CHECK
    # =========================

    if product.stock <= 0:

        flash("Sorry, this product is currently out of stock.")

        return redirect("/")
        
    # =========================
    # AUTOMATIC GST CALCULATION
    # =========================

    tax = calculate_tax(product, 1)

    taxable_amount = tax["taxable_amount"]
    gst_rate = tax["gst_rate"]
    gst_amount = tax["gst_amount"]
    final_amount = tax["total_amount"]

    # =========================
    # CREATE ORDER
    # =========================

    new_order = Order(
        customer_name=user.name or "BESTTIVE Customer",

        product_name=product.name,

        # Final amount including GST
        amount=int(final_amount),

        user_id=user.id,

        product_id=product.id,

        quantity=1,

        price=product.price,

        # Tax details
        taxable_amount=taxable_amount,

        gst_rate=gst_rate,

        gst_amount=gst_amount,

        hsn_code=product.hsn_code or "",

        # Final order total
        total_amount=final_amount,

        address=user.address or "",

        # Delivery / Order Status
        status="Pending",

        # Payment Status
        payment_status="Pending"
    )

    db.session.add(new_order)

    assign_tracking_id(new_order)

    # =========================
    # DECREASE PRODUCT STOCK
    # =========================

    previous_stock = product.stock
    product.stock -= 1

    # =========================
    # SAVE INVENTORY HISTORY
    # =========================

    inventory_history = InventoryMovement(
        product_id=product.id,
        movement_type="Sale",
        quantity=1,
        previous_stock=previous_stock,
        new_stock=product.stock,
        note=f"Sold through QR Payment | Order #{new_order.id}"
    )

    db.session.add(inventory_history)

    db.session.commit()

    # =========================
    # PAYMENT SUCCESS PAGE
    # =========================

    return render_template(
        "payment_success.html",

        customer_name=user.name,

        product_name=product.name,

        amount=final_amount,

        status="Pending",

        tracking_ids=[new_order.tracking_id]
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

    # =========================
    # CART ORDER
    # =========================

    if product_name == "BESTTIVE Shopping Cart":

        cart_items = Cart.query.filter_by(
            customer_name=customer_name
        ).all()

        total_amount = 0
        tracking_ids = []

        for item in cart_items:

            product = Product.query.get(item.product_id)

            if product:

                quantity = item.quantity or 1

                # Automatic GST calculation
                tax = calculate_tax(product, quantity)

                taxable_amount = tax["taxable_amount"]
                gst_rate = tax["gst_rate"]
                gst_amount = tax["gst_amount"]
                final_amount = tax["total_amount"]

                new_order = Order(
                    customer_name=customer_name or "BESTTIVE Customer",
                    product_name=product.name,

                    # Final amount including GST
                    amount=int(final_amount),

                    user_id=user.id,
                    product_id=product.id,

                    quantity=quantity,
                    price=product.price,

                    # Tax details
                    taxable_amount=taxable_amount,
                    gst_rate=gst_rate,
                    gst_amount=gst_amount,
                    hsn_code=product.hsn_code or "",

                    # Final total
                    total_amount=final_amount,

                    address=user.address or "",

                    # Payment Status
                    payment_status="Paid",

                    # Order / Delivery Status
                    status="Pending"
                )

                db.session.add(new_order)

                assign_tracking_id(new_order)

                tracking_ids.append(
                    new_order.tracking_id
                )

                total_amount += final_amount

                db.session.delete(item)

        db.session.commit()

        return render_template(
            "payment_success.html",
            customer_name=customer_name,
            product_name="BESTTIVE Shopping Cart",
            amount=total_amount,
            status="Pending",
            tracking_ids=tracking_ids
        )

    # =========================
    # SINGLE PRODUCT ORDER
    # =========================

    product_id = session.get("product_id")

    product = Product.query.get(product_id)

    if not product:
        flash("Product not found.")
        return redirect("/")
    
    # =========================
    # STOCK AVAILABILITY CHECK
    # =========================

    if product.stock <= 0:

        flash("Sorry, this product is currently out of stock.")

        return redirect("/")
    
    # Automatic GST calculation
    tax = calculate_tax(product, 1)

    taxable_amount = tax["taxable_amount"]
    gst_rate = tax["gst_rate"]
    gst_amount = tax["gst_amount"]
    final_amount = tax["total_amount"]

    # =========================
    # CREATE ORDER
    # =========================

    new_order = Order(
        customer_name=customer_name or "BESTTIVE Customer",
        product_name=product.name,

        # Final amount including GST
        amount=int(final_amount),

        user_id=user.id,
        product_id=product.id,

        quantity=1,
        price=product.price,

        # Tax details
        taxable_amount=taxable_amount,
        gst_rate=gst_rate,
        gst_amount=gst_amount,
        hsn_code=product.hsn_code or "",

        # Final total
        total_amount=final_amount,

        address=user.address or "",

        # Payment Status
        payment_status="Paid",

        # Order / Delivery Status
        status="Pending"
    )

    db.session.add(new_order)

    assign_tracking_id(new_order)

    # =========================
    # DECREASE PRODUCT STOCK
    # =========================
    previous_stock = product.stock
    product.stock -= 1
    inventory_history = InventoryMovement(
        product_id=product.id,
        movement_type="Sale",
        quantity=1,
        previous_stock=previous_stock,
        new_stock=product.stock,
        note=f"Sold through Buy Now | Order #{new_order.id}"
    )

    db.session.add(inventory_history)
    db.session.commit()

    return render_template(
        "payment_success.html",
        customer_name=customer_name,
        product_name=product.name,
        amount=final_amount,
        status="Pending",
        tracking_ids=[new_order.tracking_id]
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


@app.route("/about")
def about():

    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:

            return render_template(
                "contact.html",
                error="Please fill all required fields."
            )

        new_message = ContactMessage(
            name=name,
            email=email,
            phone=phone,
            message=message
        )

        db.session.add(new_message)

        db.session.commit()

        return render_template(
            "contact.html",
            success="Your message has been sent successfully!"
        )

    return render_template("contact.html")

@app.route("/track-order", methods=["GET", "POST"])
def track_order():
    order = None
    error = None

    if request.method == "POST":
        tracking_id = request.form.get("tracking_id", "").strip().upper()
        email = request.form.get("email", "").strip()

        if not tracking_id or not email:
            error = "Please enter a valid tracking ID and the email used for the order."
        else:
            # An order is shown only when its registered customer email matches.
            order = (
                Order.query
                .join(User, Order.user_id == User.id)
                .filter(
                    Order.tracking_id == tracking_id,
                    User.email.ilike(email)
                )
                .first()
            )

            if not order:
                error = "We couldn't find an order with those details."

    return render_template("track_order.html", order=order, error=error)

@app.route("/admin/complaints")
def admin_complaints():
    messages = ContactMessage.query.order_by(
        ContactMessage.id.desc()
    ).all()

    return render_template(
        "admin_complaints.html",
        messages=messages
    )
@app.route("/admin/delete-complaints", methods=["POST"])
def delete_complaints():

    complaint_ids = request.form.getlist("complaint_ids")

    for complaint_id in complaint_ids:
        complaint = ContactMessage.query.get(int(complaint_id))

        if complaint:
            db.session.delete(complaint)

    db.session.commit()

    return redirect("/admin/complaints")
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
    city = db.Column(db.String(100), default="")
    state = db.Column(db.String(100), default="")
    pincode = db.Column(db.String(20), default="")
    dob = db.Column(db.String(50), default="")
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(100), default="")
    subcategory = db.Column(db.String(100), default="")
    gst_rate = db.Column(
    db.Float,
    default=0
    )
    hsn_code = db.Column(
    db.String(20),
    default=""
    )
    # ==========================================
# BESTTIVE - HSN & GST AUTO MAPPING
# ==========================================

TAX_MAPPING = {

    # =========================
    # CLOTHES
    # =========================

    "Clothes": {

        "T-Shirts": {
            "hsn": "6109",
            "gst": 5
        },

        "Shirts": {
            "hsn": "6205",
            "gst": 5
        },

        "Jeans": {
            "hsn": "6203",
            "gst": 5
        },

        "Dresses": {
            "hsn": "6204",
            "gst": 5
        },

        "Sarees": {
            "hsn": "5208",
            "gst": 5
        }
    },


    # =========================
    # JEWELLERY
    # =========================

    "Jewellery": {

        "Bangles": {
            "hsn": "7117",
            "gst": 3
        },

        "Earrings": {
            "hsn": "7117",
            "gst": 3
        },

        "Necklace": {
            "hsn": "7117",
            "gst": 3
        },

        "Rings": {
            "hsn": "7117",
            "gst": 3
        }
    },


    # =========================
    # TOYS
    # =========================

    "Toys": {

        "Cars": {
            "hsn": "9503",
            "gst": 12
        },

        "Dolls": {
            "hsn": "9503",
            "gst": 12
        },

        "Educational Toys": {
            "hsn": "9503",
            "gst": 12
        },

        "Remote Control": {
            "hsn": "9503",
            "gst": 12
        }
    },


    # =========================
    # SHOES
    # =========================

    "Shoes": {

        "Men Shoes": {
            "hsn": "6403",
            "gst": 5
        },

        "Women Shoes": {
            "hsn": "6403",
            "gst": 5
        },

        "Kids Shoes": {
            "hsn": "6403",
            "gst": 5
        },

        "Sports Shoes": {
            "hsn": "6404",
            "gst": 5
        }
    },


    # =========================
    # WATCHES
    # =========================

    "Watches": {

        "Men Watches": {
            "hsn": "9102",
            "gst": 18
        },

        "Women Watches": {
            "hsn": "9102",
            "gst": 18
        },

        "Kids Watches": {
            "hsn": "9102",
            "gst": 18
        }
    },


    # =========================
    # ELECTRONICS
    # =========================

    "Electronics": {

        "Mobile": {
            "hsn": "8517",
            "gst": 18
        },

        "Earbuds": {
            "hsn": "8518",
            "gst": 18
        },

        "Speakers": {
            "hsn": "8518",
            "gst": 18
        },

        "Accessories": {
            "hsn": "8517",
            "gst": 18
        }
    },


    # =========================
    # BEAUTY
    # =========================

    "Beauty": {

        "Makeup": {
            "hsn": "3304",
            "gst": 18
        },

        "Skincare": {
            "hsn": "3304",
            "gst": 18
        },

        "Hair Care": {
            "hsn": "3305",
            "gst": 18
        }
    },


    # =========================
    # HOME
    # =========================

    "Home": {

        "Decor": {
            "hsn": "3926",
            "gst": 18
        },

        "Kitchen": {
            "hsn": "3924",
            "gst": 18
        },

        "Storage": {
            "hsn": "3924",
            "gst": 18
        }
    }
}

def get_tax_details(category, subcategory):

    category_data = TAX_MAPPING.get(category, {})

    tax_data = category_data.get(subcategory)

    if not tax_data:
        return {
            "hsn": "",
            "gst": 0
        }

    return {
        "hsn": tax_data["hsn"],
        "gst": tax_data["gst"]
    }

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), default="")
    message = db.Column(db.Text, nullable=False)
    
class Banner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200), default="")
    position = db.Column(db.Integer, default=1, nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow
    )

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

# ==========================================
# INVENTORY MOVEMENT HISTORY
# ==========================================

class InventoryMovement(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    movement_type = db.Column(
        db.String(50),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    previous_stock = db.Column(
        db.Integer,
        nullable=False
    )

    new_stock = db.Column(
        db.Integer,
        nullable=False
    )

    note = db.Column(
        db.String(255),
        default=""
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).replace(tzinfo=None) + datetime.timedelta(
            hours=5,
            minutes=30
        )
    )

    product = db.relationship(
        "Product",
        backref=db.backref(
            "inventory_movements",
            lazy=True
        )
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

    tracking_id = db.Column(
        db.String(30),
        unique=True,
        index=True,
        nullable=True
    )
    # =========================
    # SHIPROCKET DETAILS
    # =========================

    shiprocket_order_id = db.Column(
        db.String(50),
        nullable=True
    )

    shiprocket_shipment_id = db.Column(
        db.String(50),
        nullable=True
    )

    awb_code = db.Column(
        db.String(100),
        nullable=True
    )

    courier_name = db.Column(
        db.String(150),
        nullable=True
    )

    shiprocket_status = db.Column(
        db.String(50),
        nullable=True
    )

    # Legacy database columns retained for existing order records and invoices.
    customer_name = db.Column(db.String(100), nullable=False)

    product_name = db.Column(db.String(200), nullable=False)

    amount = db.Column(db.Integer, nullable=False)

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

    taxable_amount = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    gst_rate = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    gst_amount = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    hsn_code = db.Column(
        db.String(20),
        default=""
    )

    address = db.Column(
        db.String(255),
        default=""
    )

    # Delivery / Order Status
    status = db.Column(
        db.String(50),
        default="Pending"
    )

    # Payment Status
    payment_status = db.Column(
        db.String(30),
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow
    )

    user = db.relationship("User")

    product = db.relationship("Product")


def calculate_tax(product, quantity=1):

    quantity = int(quantity or 1)

    taxable_amount = product.price * quantity

    gst_rate = float(product.gst_rate or 0)

    gst_amount = round(
        taxable_amount * gst_rate / 100,
        2
    )

    total_amount = round(
        taxable_amount + gst_amount,
        2
    )

    return {
        "taxable_amount": taxable_amount,
        "gst_rate": gst_rate,
        "gst_amount": gst_amount,
        "total_amount": total_amount,
        "hsn_code": product.hsn_code or ""
    }

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

def assign_tracking_id(order):
    """Create the customer-facing tracking ID after an order receives its DB ID."""
    db.session.flush()
    order.tracking_id = (
        f"BB-{datetime.datetime.utcnow():%Y}-{order.id:06d}"
    )

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

    # =========================
    # DASHBOARD STATISTICS
    # =========================

    total_products = Product.query.count()

    total_customers = User.query.count()

    total_orders = Order.query.count()

    # Only Paid orders
    paid_orders = Order.query.filter_by(
        payment_status="Paid"
    ).all()

    paid_revenue = sum(
        float(order.total_amount or 0)
        for order in paid_orders
    )

    # Pending payments
    pending_payments = Order.query.filter_by(
        payment_status="Pending"
    ).count()

    # Pending delivery orders
    pending_orders = Order.query.filter_by(
        status="Pending"
    ).count()

    # Recent 5 orders
    recent_orders = (
        Order.query
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "admin_dashboard.html",

        total_products=total_products,

        total_customers=total_customers,

        total_orders=total_orders,

        paid_revenue=paid_revenue,

        pending_payments=pending_payments,

        pending_orders=pending_orders,

        recent_orders=recent_orders
    )

# ==================================================
# INVENTORY DASHBOARD
# ==================================================

@app.route("/admin/inventory")
def admin_inventory():

    # Admin login check
    if not session.get("admin"):
        return redirect("/admin")

    # ==============================================
    # INVENTORY COUNTS
    # ==============================================

    total_products = Product.query.count()

    total_stock = db.session.query(
        db.func.coalesce(
            db.func.sum(Product.stock),
            0
        )
    ).scalar()

    # फिलहाल stock 1 से 3 = Low Stock
    low_stock_count = Product.query.filter(
        Product.stock > 0,
        Product.stock <= 3
    ).count()

    out_of_stock_count = Product.query.filter(
        Product.stock <= 0
    ).count()

    # ==============================================
    # LOW STOCK PRODUCTS
    # ==============================================

    low_stock_products = Product.query.filter(
        Product.stock > 0,
        Product.stock <= 3
    ).order_by(
        Product.stock.asc()
    ).all()

    # ==============================================
    # OUT OF STOCK PRODUCTS
    # ==============================================

    out_of_stock_products = Product.query.filter(
        Product.stock <= 0
    ).all()


    # ==============================================
    # INVENTORY HISTORY PAGINATION
    # ==============================================

    page = request.args.get(
        "page",
        1,
        type=int
    )

    inventory_history = InventoryMovement.query.order_by(
        InventoryMovement.created_at.desc()
    ).paginate(
        page=page,
        per_page=10,
        error_out=False
    )


    # ==============================================
    # RENDER PAGE
    # ==============================================

    return render_template(
        "admin_inventory.html",

        total_products=total_products,

        total_stock=total_stock,

        low_stock_count=low_stock_count,

        out_of_stock_count=out_of_stock_count,

        low_stock_products=low_stock_products,

        out_of_stock_products=out_of_stock_products,

        inventory_history=inventory_history
    )

@app.route("/admin/sales")
def admin_sales():

    if not session.get("admin"):
        return redirect("/admin")

    import datetime

    # Current date
    today = datetime.datetime.utcnow().date()

    # Yesterday
    yesterday = today - datetime.timedelta(days=1)

    # Start of current week
    week_start = today - datetime.timedelta(days=today.weekday())

    # Start of current month
    month_start = today.replace(day=1)

    # Get all paid orders
    paid_orders = (
        Order.query
        .filter_by(payment_status="Paid")
        .order_by(Order.created_at.desc())
        .all()
    )

    today_sales = 0
    yesterday_sales = 0
    week_sales = 0
    month_sales = 0
    total_paid_sales = 0

    for order in paid_orders:

        amount = float(order.total_amount or 0)

        order_date = order.created_at.date()

        total_paid_sales += amount

        if order_date == today:
            today_sales += amount

        if order_date == yesterday:
            yesterday_sales += amount

        if order_date >= week_start:
            week_sales += amount

        if order_date >= month_start:
            month_sales += amount

    return render_template(
        "admin_sales.html",
        today_sales=today_sales,
        yesterday_sales=yesterday_sales,
        week_sales=week_sales,
        month_sales=month_sales,
        total_paid_sales=total_paid_sales,
        paid_orders=paid_orders
    )

@app.route("/admin/payment")
def admin_payment():

    if not session.get("admin"):
        return redirect("/admin")

    # All orders with payment information
    payments = (
        Order.query
        .order_by(Order.created_at.desc())
        .all()
    )

    # Payment counts
    total_payments = len(payments)

    paid_payments = sum(
        1 for order in payments
        if order.payment_status == "Paid"
    )

    pending_payments = sum(
        1 for order in payments
        if order.payment_status == "Pending"
    )

    not_received_payments = sum(
        1 for order in payments
        if order.payment_status == "Not Received"
    )

    return render_template(
        "admin_payment.html",
        payments=payments,
        total_payments=total_payments,
        paid_payments=paid_payments,
        pending_payments=pending_payments,
        not_received_payments=not_received_payments
    )

@app.route("/admin/pending-payments")
def admin_pending_payments():

    if not session.get("admin"):
        return redirect("/admin")

    pending_orders = (
        Order.query
        .filter_by(payment_status="Pending")
        .order_by(Order.created_at.desc())
        .all()
    )

    return render_template(
        "admin_pending_payments.html",
        orders=pending_orders
    )

# =========================
# ADMIN BANNER MANAGEMENT
# =========================

@app.route("/admin/banners")
def admin_banners():

    if not session.get("admin"):
        return redirect("/admin")

    banners = Banner.query.order_by(Banner.id.desc()).all()

    return render_template(
        "admin_banners.html",
        banners=banners
    )

# =========================
# ADD BANNER
# =========================

@app.route("/admin/banners/add", methods=["POST"])
def add_banner():

    if not session.get("admin"):
        return redirect("/admin")

    image = request.files.get("image")
    title = request.form.get("title", "").strip()
    position = request.form.get("position", "1")

    if not image or image.filename == "":
        flash("Please select a banner image.")
        return redirect("/admin/banners")

    try:
        position = int(position)

        if position < 1 or position > 8:
            flash("Banner position must be between 1 and 8.")
            return redirect("/admin/banners")

    except ValueError:
        flash("Invalid banner position.")
        return redirect("/admin/banners")

    # Check whether position is already occupied
    existing_banner = Banner.query.filter_by(
        position=position
    ).first()

    if existing_banner:
        flash(f"Position {position} is already occupied.")
        return redirect("/admin/banners")

    # Upload image to Cloudinary
    upload_result = cloudinary.uploader.upload(
        image,
        folder="besttive/banners"
    )

    image_url = upload_result["secure_url"]

    new_banner = Banner(
        image=image_url,
        title=title,
        position=position,
        active=True
    )

    db.session.add(new_banner)
    db.session.commit()

    flash("Banner added successfully!")

    return redirect("/admin/banners")


# =========================
# CHANGE / REPLACE BANNER
# =========================

@app.route("/admin/banners/<int:id>/update", methods=["POST"])
def update_banner(id):

    if not session.get("admin"):
        return redirect("/admin")

    banner = Banner.query.get_or_404(id)

    title = request.form.get("title", "").strip()
    position = request.form.get("position", str(banner.position))

    try:
        position = int(position)

        if position < 1 or position > 8:
            flash("Banner position must be between 1 and 8.")
            return redirect("/admin/banners")

    except ValueError:
        flash("Invalid banner position.")
        return redirect("/admin/banners")

    # Check duplicate position
    existing_banner = Banner.query.filter(
        Banner.position == position,
        Banner.id != banner.id
    ).first()

    if existing_banner:
        flash(f"Position {position} is already occupied.")
        return redirect("/admin/banners")

    image = request.files.get("image")

    if image and image.filename != "":
        upload_result = cloudinary.uploader.upload(
            image,
            folder="besttive/banners"
        )

        banner.image = upload_result["secure_url"]

    banner.title = title
    banner.position = position

    db.session.commit()

    flash("Banner updated successfully!")

    return redirect("/admin/banners")


# =========================
# DELETE BANNER
# =========================

@app.route("/admin/banners/<int:id>/delete")
def delete_banner(id):

    if not session.get("admin"):
        return redirect("/admin")

    banner = Banner.query.get_or_404(id)

    db.session.delete(banner)
    db.session.commit()

    flash("Banner deleted successfully!")

    return redirect("/admin/banners")


# =========================
# TOGGLE BANNER ACTIVE
# =========================

@app.route("/admin/banners/<int:id>/toggle")
def toggle_banner(id):

    if not session.get("admin"):
        return redirect("/admin")

    banner = Banner.query.get_or_404(id)

    banner.active = not banner.active

    db.session.commit()

    flash("Banner status updated!")

    return redirect("/admin/banners")

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
        category = request.form.get("category")
        subcategory = request.form.get("subcategory")

        # ==========================================
        # AUTO HSN + GST
        # ==========================================

        tax_details = get_tax_details(
            category,
            subcategory
        )

        hsn_code = tax_details["hsn"]
        gst_rate = tax_details["gst"]

        # ==========================================
        # MAIN IMAGE
        # ==========================================

        image = request.files["image"]

        upload_result = cloudinary.uploader.upload(image)
        image_url = upload_result["secure_url"]

        # ==========================================
        # CREATE PRODUCT
        # ==========================================

        new_product = Product(
            name=name,
            price=int(price),
            image=image_url,
            description=description,
            stock=int(stock or 0),

            category=category,
            subcategory=subcategory,

            # Automatically assigned
            hsn_code=hsn_code,
            gst_rate=float(gst_rate)
        )

        db.session.add(new_product)
        db.session.commit()

        # ==========================================
        # EXTRA IMAGES
        # ==========================================

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

        flash(
            f"Product Added Successfully! "
            f"HSN: {hsn_code or 'Not assigned'} | "
            f"GST: {gst_rate}%"
        )

        return redirect("/admin/dashboard")

    return render_template(
        "add_product.html"
    )

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

    # Admin login check
    if not session.get("admin"):
        return redirect("/admin")

    product = Product.query.get_or_404(id)

    if request.method == "POST":

        # ==========================================
        # BASIC PRODUCT DETAILS
        # ==========================================

        product.name = request.form.get("name", "").strip()

        product.price = int(
            request.form.get("price") or 0
        )

        product.description = request.form.get(
            "description",
            ""
        )

        # ==========================================
        # STOCK UPDATE + INVENTORY HISTORY
        # ==========================================

        previous_stock = product.stock
        new_stock = int(
            request.form.get("stock") or 0
        )

        product.stock = new_stock
        
        # Calculate stock difference
        stock_difference = new_stock - previous_stock

        # Save history only if stock changed
        if stock_difference != 0:

            if stock_difference > 0:
                movement_type = "Stock Added"
            else:
                movement_type = "Stock Removed"

            inventory_history = InventoryMovement(
                product_id=product.id,
                movement_type=movement_type,
                quantity=(stock_difference),
                previous_stock=previous_stock,
                new_stock=new_stock,
                note="Manual stock update from Admin"
            )

            db.session.add(inventory_history)


        # ==========================================
        # CATEGORY + SUBCATEGORY
        # ==========================================

        category = request.form.get(
            "category",
            ""
        )

        subcategory = request.form.get(
            "subcategory",
            ""
        )

        product.category = category
        product.subcategory = subcategory


        # ==========================================
        # AUTO HSN + GST
        # ==========================================

        tax_details = get_tax_details(
            category,
            subcategory
        )

        product.hsn_code = tax_details["hsn"]

        product.gst_rate = float(
            tax_details["gst"]
        )


        # ==========================================
        # IMAGE UPDATE
        # ==========================================

        image = request.files.get("image")

        if image and image.filename != "":

            upload_result = cloudinary.uploader.upload(
                image
            )

            product.image = upload_result[
                "secure_url"
            ]


        # ==========================================
        # SAVE EVERYTHING
        # ==========================================

        db.session.commit()


        flash(
            f"Product Updated Successfully! "
            f"HSN: {product.hsn_code or 'Not assigned'} | "
            f"GST: {product.gst_rate:g}%"
        )


        return redirect(
            "/admin/products"
        )


    return render_template(
        "edit_product.html",
        product=product
    )

# =========================
# DELETE INVENTORY HISTORY
# =========================

@app.route(
    "/admin/delete-inventory-history",
    methods=["POST"]
)
def delete_inventory_history():

    # Admin login check
    if not session.get("admin"):
        return redirect("/admin")


    movement_ids = request.form.getlist(
        "movement_ids"
    )


    # Nothing selected
    if not movement_ids:

        flash(
            "Please select at least one history record."
        )

        return redirect(
            "/admin/inventory"
        )


    # Delete selected records
    InventoryMovement.query.filter(
        InventoryMovement.id.in_(movement_ids)
    ).delete(
        synchronize_session=False
    )


    db.session.commit()


    flash(
        f"{len(movement_ids)} inventory history record(s) deleted successfully!"
    )


    return redirect(
        "/admin/inventory"
    )

@app.route("/admin/orders")
def admin_orders():

    if not session.get("admin"):
        return redirect("/admin")

    orders = Order.query.order_by(Order.id.desc()).all()

    return render_template(
        "admin_orders.html",
        orders=orders
    )

# ==================================================
# SHIPROCKET SHIPPING DASHBOARD
# ==================================================

@app.route("/admin/shipping")
def admin_shipping():

    # Admin login check
    if not session.get("admin"):
        return redirect("/admin")

    # Only orders that have a Shiprocket shipment
    shipments = (
        Order.query
        .filter(
            Order.shiprocket_shipment_id.isnot(None)
        )
        .order_by(Order.id.desc())
        .all()
    )

    return render_template(
        "admin_shipping.html",
        shipments=shipments
    )

@app.route("/admin/update-order-status/<int:id>", methods=["POST"])
def update_order_status(id):

    if not session.get("admin"):
        return redirect("/admin")

    order = Order.query.get_or_404(id)

    order.status = request.form["status"]

    db.session.commit()

    flash("Order Status Updated Successfully!")

    return redirect("/admin/dashboard")

@app.route("/admin/update-payment-status/<int:id>", methods=["POST"])
def update_payment_status(id):

    if not session.get("admin"):
        return redirect("/admin")

    order = Order.query.get_or_404(id)

    payment_status = request.form.get("payment_status")

    if payment_status == "Paid":

        order.payment_status = "Paid"

        # Payment paid hai,
        # lekin delivery/order abhi pending rahega
        if order.status == "Payment Verification":
            order.status = "Pending"

        flash("Payment marked as Paid successfully!")

    elif payment_status == "Not Received":

        order.payment_status = "Not Received"

        # Order ko cancel nahi karna.
        # Customer baad mein payment kar sakta hai.
        if order.status == "Payment Verification":
            order.status = "Pending"

        flash("Payment marked as Not Received.")

    elif payment_status == "Pending":

        order.payment_status = "Pending"

        flash("Payment marked as Pending.")

    db.session.commit()

    return redirect(request.referrer or "/admin/payment")
    
@app.route("/admin/delete-orders", methods=["POST"])
def delete_orders():

    order_ids = request.form.getlist("order_ids")

    for order_id in order_ids:

        order = Order.query.get(int(order_id))

        if order:
            db.session.delete(order)

    db.session.commit()

    return redirect("/admin/orders")

@app.route("/admin/customers")
def admin_customers():

    if not session.get("admin"):
        return redirect("/admin")

    customers = User.query.all()

    customer_stats = {}

    for customer in customers:

        orders = Order.query.filter_by(
            user_id=customer.id
        ).all()

        # Cancelled orders ko exclude karo
        valid_orders = [
            order
            for order in orders
            if order.status != "Cancelled"
        ]

        total_orders = len(valid_orders)

        total_spent = sum(
            float(order.total_amount or 0)
            for order in valid_orders
        )

        customer_stats[customer.id] = {
            "total_orders": total_orders,
            "total_spent": total_spent
        }

    return render_template(
        "admin_customers.html",
        customers=customers,
        customer_stats=customer_stats
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

    # =========================
    # COLORS
    # =========================

    PURPLE = colors.HexColor("#54206F")
    DARK_PURPLE = colors.HexColor("#3D1259")
    LIGHT_PURPLE = colors.HexColor("#F7F1FA")
    GOLD = colors.HexColor("#C99A35")
    LIGHT_GOLD = colors.HexColor("#FFF7E5")
    TEXT = colors.HexColor("#29232D")
    GREY = colors.HexColor("#777777")
    BORDER = colors.HexColor("#E2D8E7")
    WHITE = colors.white

    # =========================
    # PDF DOCUMENT
    # =========================

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm
    )

    styles = getSampleStyleSheet()

    # =========================
    # STYLES
    # =========================

    brand_style = ParagraphStyle(
        "Brand",
        parent=styles["Normal"],
        fontName="DejaVuSans-Bold",
        fontSize=25,
        leading=28,
        alignment=TA_CENTER,
        textColor=PURPLE
    )

    tagline_style = ParagraphStyle(
        "Tagline",
        parent=styles["Normal"],
        fontName="DejaVuSans-Bold",
        fontSize=8,
        leading=11,
        alignment=TA_CENTER,
        textColor=GOLD
    )

    invoice_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Normal"],
        fontName="DejaVuSans-Bold",
        fontSize=23,
        leading=27,
        alignment=TA_RIGHT,
        textColor=PURPLE
    )

    order_no_style = ParagraphStyle(
        "OrderNo",
        parent=styles["Normal"],
        fontName="DejaVuSans-Bold",
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT,
        textColor=GOLD
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Normal"],
        fontName="DejaVuSans-Bold",
        fontSize=8.5,
        leading=11,
        textColor=PURPLE
    )

    normal_style = ParagraphStyle(
        "NormalCustom",
        parent=styles["Normal"],
        fontName="DejaVuSans",
        fontSize=9,
        leading=13,
        textColor=TEXT
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontName="DejaVuSans",
        fontSize=8,
        leading=11,
        textColor=GREY
    )

    right_style = ParagraphStyle(
        "Right",
        parent=normal_style,
        fontName="DejaVuSans",
        alignment=TA_RIGHT
    )

    center_style = ParagraphStyle(
        "Center",
        parent=normal_style,
        fontName="DejaVuSans",
        alignment=TA_CENTER
    )

    white_center_style = ParagraphStyle(
        "WhiteCenter",
        parent=normal_style,
        fontName="DejaVuSans-Bold",
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=WHITE
    )

    footer_brand_style = ParagraphStyle(
        "FooterBrand",
        parent=styles["Normal"],
        fontName="DejaVuSans-Bold",
        fontSize=17,
        leading=20,
        alignment=TA_CENTER,
        textColor=GOLD
    )

    footer_features_style = ParagraphStyle(
        "FooterFeatures",
        parent=styles["Normal"],
        fontName="DejaVuSans-Bold",
        fontSize=8,
        leading=11,
        alignment=TA_CENTER,
        textColor=WHITE
    )

    story = []

    # =========================
    # TAX / ORDER VALUES
    # =========================

    quantity = order.quantity or 1

    unit_price = (
        order.price
        if order.price is not None
        else order.amount
    )

    taxable_amount = (
        order.taxable_amount
        if order.taxable_amount is not None
        else unit_price * quantity
    )

    gst_rate = (
        order.gst_rate
        if order.gst_rate is not None
        else 0
    )

    gst_amount = (
        order.gst_amount
        if order.gst_amount is not None
        else 0
    )

    grand_total = (
        order.total_amount
        if order.total_amount is not None
        else order.amount
    )

    hsn_code = order.hsn_code or "—"

    # =========================
    # HEADER
    # =========================

    header_table = Table(
        [[
            "",
            [
                Paragraph(
                    "BESTTIVE",
                    brand_style
                ),
                Spacer(1, 1.5 * mm),
                Paragraph(
                    "STYLE THAT SHINES",
                    tagline_style
                )
            ],
            [
                Paragraph(
                    "INVOICE",
                    invoice_style
                ),
                Spacer(1, 1.5 * mm),
                Paragraph(
                    f"ORDER NO. &nbsp; #{order.id}",
                    order_no_style
                )
            ]
        ]],
        colWidths=[
            25 * mm,
            85 * mm,
            60 * mm
        ]
    )

    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0)
        ])
    )

    story.append(header_table)

    story.append(
        Spacer(1, 6 * mm)
    )

    # =========================
    # PURPLE / GOLD LINE
    # =========================

    top_line = Table(
        [[""]],
        colWidths=[170 * mm],
        rowHeights=[2.5 * mm]
    )

    top_line.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PURPLE),
            ("LINEBELOW", (0, 0), (-1, -1), 1, GOLD)
        ])
    )

    story.append(top_line)

    story.append(
        Spacer(1, 6 * mm)
    )

    # =========================
    # BILL TO / ORDER DETAILS
    # =========================

    customer_block = [
        Paragraph(
            "BILL TO",
            section_style
        ),

        Spacer(1, 2 * mm),

        Paragraph(
            f"<b>{order.customer_name}</b>",
            normal_style
        ),

        Spacer(1, 1.5 * mm),

        Paragraph(
            order.address or "Address not available",
            small_style
        )
    ]

    order_block = [
        Paragraph(
            "ORDER DETAILS",
            section_style
        ),

        Spacer(1, 2 * mm),

        Paragraph(
            f"<b>Order ID:</b> #{order.id}",
            normal_style
        ),

        Paragraph(
            f"<b>Date:</b> "
            f"{order.created_at.strftime('%d %b %Y, %I:%M %p')}",
            normal_style
        ),

        Paragraph(
            f"<b>Status:</b> {order.status}",
            normal_style
        )
    ]

    info_table = Table(
        [[
            customer_block,
            order_block
        ]],
        colWidths=[
            85 * mm,
            85 * mm
        ]
    )

    info_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_PURPLE),

            ("BOX", (0, 0), (-1, -1), 0.7, BORDER),

            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),

            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            ("LEFTPADDING", (0, 0), (-1, -1), 11),
            ("RIGHTPADDING", (0, 0), (-1, -1), 11),

            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10)
        ])
    )

    story.append(info_table)

    story.append(
        Spacer(1, 7 * mm)
    )

    # =========================
    # PRODUCT TABLE
    # =========================

    product_data = [
        [
            Paragraph(
                "PRODUCT",
                white_center_style
            ),

            Paragraph(
                "HSN",
                white_center_style
            ),

            Paragraph(
                "QTY",
                white_center_style
            ),

            Paragraph(
                "RATE",
                white_center_style
            ),

            Paragraph(
                "TAXABLE",
                white_center_style
            )
        ],

        [
            Paragraph(
                f"<b>{order.product_name}</b><br/>"
                f"<font size='7' color='#777777'>"
                f"BESTTIVE Product"
                f"</font>",
                normal_style
            ),

            Paragraph(
                hsn_code,
                center_style
            ),

            Paragraph(
                str(quantity),
                center_style
            ),

            Paragraph(
                f"₹{unit_price:.2f}",
                right_style
            ),

            Paragraph(
                f"₹{taxable_amount:.2f}",
                right_style
            )
        ]
    ]

    product_table = Table(
        product_data,
        colWidths=[
            60 * mm,
            22 * mm,
            18 * mm,
            32 * mm,
            38 * mm
        ],
        repeatRows=1
    )

    product_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PURPLE),

            ("BACKGROUND", (0, 1), (-1, -1), WHITE),

            ("BOX", (0, 0), (-1, -1), 0.8, BORDER),

            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),

            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9)
        ])
    )

    story.append(product_table)

    story.append(
        Spacer(1, 6 * mm)
    )

    # =========================
    # GST SUMMARY
    # =========================

    gst_summary = [
        [
            Paragraph(
                "Taxable Amount",
                normal_style
            ),

            Paragraph(
                f"₹{taxable_amount:.2f}",
                right_style
            )
        ],

        [
            Paragraph(
                f"GST ({gst_rate:g}%)",
                normal_style
            ),

            Paragraph(
                f"₹{gst_amount:.2f}",
                right_style
            )
        ]
    ]

    gst_table = Table(
        gst_summary,
        colWidths=[
            115 * mm,
            55 * mm
        ]
    )

    gst_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GOLD),

            ("BOX", (0, 0), (-1, -1), 0.7, GOLD),

            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),

            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)
        ])
    )

    story.append(gst_table)

    story.append(
        Spacer(1, 5 * mm)
    )

    # =========================
    # GRAND TOTAL
    # =========================

    total_table = Table(
        [[
            Paragraph(
                "<b>GRAND TOTAL</b>",
                normal_style
            ),

            Paragraph(
                f"<b>₹{grand_total:.2f}</b>",
                right_style
            )
        ]],
        colWidths=[
            115 * mm,
            55 * mm
        ]
    )

    total_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_PURPLE),

            ("BOX", (0, 0), (-1, -1), 1, PURPLE),

            ("TEXTCOLOR", (0, 0), (-1, -1), PURPLE),

            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),

            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10)
        ])
    )

    story.append(total_table)

    story.append(
        Spacer(1, 6 * mm)
    )

    # =========================
    # TRACKING ID
    # =========================

    if order.tracking_id:

        tracking_table = Table(
            [[
                Paragraph(
                    "<b>TRACKING ID</b>",
                    section_style
                ),

                Paragraph(
                    f"<b>{order.tracking_id}</b>",
                    right_style
                )
            ]],
            colWidths=[
                65 * mm,
                105 * mm
            ]
        )

        tracking_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GOLD),

                ("BOX", (0, 0), (-1, -1), 0.7, GOLD),

                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),

                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
            ])
        )

        story.append(tracking_table)

        story.append(
            Spacer(1, 6 * mm)
        )

    # =========================
    # THANK YOU
    # =========================

    thank_you = Table(
        [[
            Paragraph(
                "<b>Thank You for Shopping with BESTTIVE!</b><br/>"
                "<font size='8' color='#777777'>"
                "We truly appreciate your trust and support."
                "</font>",
                center_style
            )
        ]],
        colWidths=[170 * mm]
    )

    thank_you.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_PURPLE),

            ("BOX", (0, 0), (-1, -1), 0.7, BORDER),

            ("ALIGN", (0, 0), (-1, -1), "CENTER"),

            ("TOPPADDING", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 11)
        ])
    )

    story.append(thank_you)

    story.append(
        Spacer(1, 5 * mm)
    )

    # =========================
    # FOOTER
    # =========================

    footer_table = Table(
        [
            [
                Paragraph(
                    "BESTTIVE",
                    footer_brand_style
                )
            ],

            [
                Paragraph(
                    "Premium Quality"
                    " &nbsp;&nbsp; | &nbsp;&nbsp; "
                    "Secure Payment"
                    " &nbsp;&nbsp; | &nbsp;&nbsp; "
                    "Fast Delivery",
                    footer_features_style
                )
            ]
        ],
        colWidths=[170 * mm],
        rowHeights=[
            14 * mm,
            10 * mm
        ]
    )

    footer_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), DARK_PURPLE),

            ("ALIGN", (0, 0), (-1, -1), "CENTER"),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),

            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5)
        ])
    )

    story.append(footer_table)

    # =========================
    # BUILD PDF
    # =========================

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
@app.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
def toggle_wishlist(product_id):

    if not session.get("user_id"):
        return {"success": False, "login": True}, 401

    user_id = session["user_id"]

    user = User.query.get(user_id)

    if not user:
        session.clear()
        return {"success": False, "login": True}, 401

    product = Product.query.get_or_404(product_id)

    existing = Wishlist.query.filter_by(
        user_id=user_id,
        product_id=product.id
    ).first()

    if existing:

        db.session.delete(existing)
        db.session.commit()

        return {
            "success": True,
            "added": False
        }

    else:

        item = Wishlist(
            user_id=user_id,
            product_id=product.id
        )

        db.session.add(item)
        db.session.commit()

        return {
            "success": True,
            "added": True
        }
    
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
        user.city = request.form.get("city")
        user.state = request.form.get("state")
        user.pincode = request.form.get("pincode")
        user.phone = request.form.get("phone")
        user.dob = request.form.get("dob")
        db.session.commit()
        return redirect("/profile")

    return render_template("profile.html", user=user)

# ==================================================
# SHIPROCKET PARCEL DETAILS PAGE
# ==================================================

@app.route("/admin/shiprocket/<int:order_id>")
def shiprocket_parcel_details(order_id):

    # Admin login check
    if not session.get("admin"):
        return redirect("/admin")

    # Get order
    order = Order.query.get_or_404(order_id)

    return render_template(
        "shiprocket_parcel.html",
        order=order
    )


# ==================================================
# CREATE SHIPROCKET ORDER
# ==================================================

@app.route(
    "/admin/shiprocket/create/<int:order_id>",
    methods=["POST"]
)
def create_shiprocket_order(order_id):

    # Admin login check
    if not session.get("admin"):
        return redirect("/admin")

    # Get order
    order = Order.query.get_or_404(order_id)

    # Customer
    user = order.user

    # Product
    product = order.product

    # ==============================================
    # GET ACTUAL PARCEL DETAILS
    # ==============================================

    weight = request.form.get("weight", type=float)

    length = request.form.get("length", type=float)

    breadth = request.form.get("breadth", type=float)

    height = request.form.get("height", type=float)


    # ==============================================
    # VALIDATION
    # ==============================================

    if not weight or weight <= 0:

        flash("Please enter a valid parcel weight.")

        return redirect(
            f"/admin/shiprocket/{order.id}"
        )


    if not length or length <= 0.5:

        flash(
            "Length must be greater than 0.5 cm."
        )

        return redirect(
            f"/admin/shiprocket/{order.id}"
        )


    if not breadth or breadth <= 0.5:

        flash(
            "Breadth must be greater than 0.5 cm."
        )

        return redirect(
            f"/admin/shiprocket/{order.id}"
        )


    if not height or height <= 0.5:

        flash(
            "Height must be greater than 0.5 cm."
        )

        return redirect(
            f"/admin/shiprocket/{order.id}"
        )


    # ==============================================
    # CUSTOMER ADDRESS VALIDATION
    # ==============================================

    if not user.address:

        flash(
            "Customer address is missing."
        )

        return redirect(
            "/admin/orders"
        )


    if not user.city:

        flash(
            "Customer city is missing."
        )

        return redirect(
            "/admin/orders"
        )


    if not user.state:

        flash(
            "Customer state is missing."
        )

        return redirect(
            "/admin/orders"
        )


    if not user.pincode:

        flash(
            "Customer pincode is missing."
        )

        return redirect(
            "/admin/orders"
        )


    if not user.phone:

        flash(
            "Customer phone number is missing."
        )

        return redirect(
            "/admin/orders"
        )


    # ==============================================
    # GET SHIPROCKET TOKEN
    # ==============================================

    token = get_shiprocket_token()


    if not token:

        flash(
            "Shiprocket authentication failed."
        )

        return redirect(
            "/admin/orders"
        )


    # ==============================================
    # PAYMENT METHOD
    # ==============================================

    if order.payment_status == "Paid":

        payment_method = "Prepaid"

    else:

        payment_method = "COD"


    # ==============================================
    # PICKUP LOCATION
    # ==============================================

    pickup_location = os.getenv(
        "SHIPROCKET_PICKUP_LOCATION",
        "Home"
    )


    # ==============================================
    # SHIPROCKET ORDER ID
    # Unique ID required for Shiprocket
    # ==============================================

    shiprocket_order_number = (
        f"BESTTIVE-{order.id}"
    )


    # ==============================================
    # ORDER DATE
    # ==============================================

    order_date = order.created_at.strftime(
        "%Y-%m-%d %H:%M"
    )


    # ==============================================
    # PRODUCT PRICE
    # ==============================================

    product_price = float(
        order.price or 0
    )


    # ==============================================
    # SUB TOTAL
    # ==============================================

    sub_total = float(
        order.taxable_amount
        or order.total_amount
        or order.amount
        or 0
    )


    # ==============================================
    # SHIPROCKET API URL
    # ==============================================

    url = (
        "https://apiv2.shiprocket.in/"
        "v1/external/orders/create/adhoc"
    )


    # ==============================================
    # REQUEST HEADERS
    # ==============================================

    headers = {

        "Content-Type":
            "application/json",

        "Authorization":
            f"Bearer {token}"

    }


    # ==============================================
    # SHIPROCKET ORDER PAYLOAD
    # ==============================================

    payload = {

        # ORDER

        "order_id":
            shiprocket_order_number,

        "order_date":
            order_date,

        "pickup_location":
            pickup_location,


        # CUSTOMER

        "billing_customer_name":
            user.name or "BESTTIVE Customer",

        "billing_last_name":
            "",

        "billing_address":
            user.address,

        "billing_address_2":
            "",

        "billing_city":
            user.city,

        "billing_pincode":
            str(user.pincode),

        "billing_state":
            user.state,

        "billing_country":
            "India",

        "billing_email":
            user.email,

        "billing_phone":
            str(user.phone),


        # SHIPPING SAME AS BILLING

        "shipping_is_billing":
            True,


        # PRODUCT

        "order_items": [

            {

                "name":
                    product.name,

                "sku":
                    f"BESTTIVE-{product.id}",

                "units":
                    int(order.quantity or 1),

                "selling_price":
                    product_price,

                "discount":
                    0,

                "tax":
                    float(order.gst_rate or 0),

                "hsn":
                    order.hsn_code or ""

            }

        ],


        # PAYMENT

        "payment_method":
            payment_method,


        # CHARGES

        "shipping_charges":
            0,

        "giftwrap_charges":
            0,

        "transaction_charges":
            0,

        "total_discount":
            0,


        # ORDER VALUE

        "sub_total":
            sub_total,


        # ACTUAL PACKED PARCEL DETAILS

        "length":
            length,

        "breadth":
            breadth,

        "height":
            height,

        "weight":
            weight

    }

    # ==============================================
    # SEND ORDER TO SHIPROCKET
    # ==============================================

    try:
        response = requests.post(

            url,

            json=payload,

            headers=headers,

            timeout=30
        )

        data = response.json()
        print("=================================")
        print("SHIPROCKET RESPONSE STATUS:", response.status_code)
        print("SHIPROCKET RESPONSE DATA:", data)
        print("=================================")

        # ==========================================
        # SUCCESS
        # ==========================================
                
        if response.status_code in [200, 201]:

            print(
                "Shiprocket Order Created:",
                data
            )

            # ======================================
            # SAVE SHIPROCKET DETAILS IN DATABASE
            # ======================================

            order.shiprocket_order_id = str(
                data.get("order_id", "")
            )

            order.shiprocket_shipment_id = str(
                data.get("shipment_id", "")
            )

            order.shiprocket_status = data.get(
                "status",
                "NEW"
            )

            order.awb_code = data.get(
                "awb_code",
                ""
            )

            order.courier_name = data.get(
                "courier_name",
                ""
            )

            # Save all Shiprocket details
            db.session.commit()

            print(
                "Shiprocket details saved successfully!"
            )

            flash(
                "Order successfully created in Shiprocket!"
            )

            return redirect(
                "/admin/orders"
            )


        # ==========================================
        # ERROR FROM SHIPROCKET
        # ==========================================

        print(
            "Shiprocket Order Error:",
            data
        )


        flash(
            f"Shiprocket Error: {data}"
        )


        return redirect(
            f"/admin/shiprocket/{order.id}"
        )


    # ==============================================
    # CONNECTION ERROR
    # ==============================================

    except Exception as e:

        print(
            "Shiprocket Request Error:",
            e
        )


        flash(
            f"Shiprocket connection error: {e}"
        )


        return redirect(
            f"/admin/shiprocket/{order.id}"
        )

# ==================================================
# GET SHIPROCKET COURIER OPTIONS
# ==================================================

@app.route("/admin/shipping/couriers/<int:order_id>")
def shiprocket_couriers(order_id):

    # Admin login check
    if not session.get("admin"):
        return redirect("/admin")

    order = Order.query.get_or_404(order_id)
    user = order.user
    
    # Shipment must exist
    if not order.shiprocket_shipment_id:

        flash("Shiprocket shipment not found.")

        return redirect("/admin/shipping")

    # Get Shiprocket token
    token = get_shiprocket_token()

    if not token:

        flash("Shiprocket authentication failed.")

        return redirect("/admin/shipping")

    try:

        # Shiprocket courier recommendation API
        url = (
            "https://apiv2.shiprocket.in/v1/external/"
            "courier/serviceability/"
        )

        params = {

            "pickup_postcode":
                os.getenv(
                    "SHIPROCKET_PICKUP_PINCODE"
                ),

            "delivery_postcode":
                user.pincode,

            "order_id":
                int(order.shiprocket_order_id)

        }

        headers = {

            "Authorization":
                f"Bearer {token}"

        }

        response = requests.get(

            url,

            params=params,

            headers=headers,

            timeout=30

        )

        data = response.json()

        print("=================================")
        print(
            "SHIPROCKET COURIER RESPONSE:",
            response.status_code
        )
        print(data)
        print("=================================")

        if response.status_code == 200:

            couriers = data.get(
                "data",
                {}).get(
                    "available_courier_companies",
                    []
                )

            return render_template(

                "shiprocket_couriers.html",

                order=order,

                couriers=couriers

            )

        flash(f"Courier Error: {data}")

        return redirect("/admin/shipping")

    except Exception as e:

        print("Shiprocket Courier Error:", e)

        flash("Unable to fetch courier options.")

        return redirect("/admin/shipping")

# ==================================================
# SELECT COURIER AND GENERATE AWB
# ==================================================

@app.route(
    "/admin/shipping/select-courier/<int:order_id>",
    methods=["POST"]
)
def select_shiprocket_courier(order_id):

    # Admin login check
    if not session.get("admin"):
        return redirect("/admin")

    # Get order
    order = Order.query.get_or_404(order_id)

    # Get selected courier details
    courier_company_id = request.form.get(
        "courier_company_id"
    )

    courier_name = request.form.get(
        "courier_name"
    )

    # Shipment validation
    if not order.shiprocket_shipment_id:

        flash(
            "Shiprocket shipment not found."
        )

        return redirect(
            "/admin/shipping"
        )

    # Courier validation
    if not courier_company_id:

        flash(
            "Please select a courier."
        )

        return redirect(
            f"/admin/shipping/couriers/{order.id}"
        )

    # Get Shiprocket token
    token = get_shiprocket_token()

    if not token:

        flash(
            "Shiprocket authentication failed."
        )

        return redirect(
            "/admin/shipping"
        )

    try:

        # ==========================================
        # GENERATE AWB API
        # ==========================================

        url = (
            "https://apiv2.shiprocket.in/"
            "v1/external/courier/assign/awb"
        )

        payload = {

            "shipment_id":
                int(order.shiprocket_shipment_id),

            "courier_id":
                int(courier_company_id)

        }

        headers = {

            "Authorization":
                f"Bearer {token}",

            "Content-Type":
                "application/json"

        }

        response = requests.post(

            url,

            json=payload,

            headers=headers,

            timeout=30

        )

        data = response.json()

        print("=================================")
        print(
            "SHIPROCKET AWB RESPONSE STATUS:",
            response.status_code
        )
        print(
            "SHIPROCKET AWB RESPONSE DATA:",
            data
        )
        print("=================================")


        # ==========================================
        # SUCCESS
        # ==========================================

        if response.status_code in [200, 201]:

            # Save selected courier
            order.courier_name = courier_name or ""

            # Shiprocket may return AWB inside data
            awb_data = data.get(
                "response",
                {}
            )

            order.awb_code = (
                awb_data.get("data", {})
                .get("awb_code", "")
            )

            # Fallback locations
            if not order.awb_code:

                order.awb_code = (
                    data.get("awb_code")
                    or data.get("data", {})
                    .get("awb_code", "")
                )

            # Update status
            order.shiprocket_status = "AWB Assigned"

            # Save database
            db.session.commit()

            print(
                "AWB generated successfully:",
                order.awb_code
            )

            flash(
                f"Courier selected successfully: "
                f"{courier_name}. AWB generated!"
            )

            return redirect(
                "/admin/shipping"
            )


        # ==========================================
        # ERROR
        # ==========================================

        print(
            "Shiprocket AWB Error:",
            data
        )

        flash(
            f"AWB Generation Error: {data}"
        )

        return redirect(
            f"/admin/shipping/couriers/{order.id}"
        )


    # ==============================================
    # CONNECTION ERROR
    # ==============================================

    except Exception as e:

        print(
            "Shiprocket AWB Connection Error:",
            e
        )

        flash(
            "Unable to generate AWB. "
            "Please check the terminal."
        )

        return redirect(
            f"/admin/shipping/couriers/{order.id}"
        )
    
if __name__ == "__main__":
    app.run(debug=False)
