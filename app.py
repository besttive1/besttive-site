from flask import Flask, render_template, request, redirect

app = Flask(__name__)   # 👉 YE SABSE PEHLE hona chahiye

products = [
    {"name": "Bangles Set", "price": 299, "image": "images/bangles.jpg"},
    {"name": "Mobile Phone", "price": 12999, "image": "images/mobile.jpg"},
    {"name": "Toys", "price": 399, "image": "images/toy.jpg"},
]

cart = []

@app.route("/")
def home():
    return render_template("home.html", products=products)

from flask import Flask, render_template

app = Flask(__name__)

# PRODUCTS (example)
products = [
    {"name": "Bangles Set", "price": 299, "image": "images/bangles.jpg"},
    {"name": "Mobile Phone", "price": 12999, "image": "images/mobile.jpg"},
    {"name": "Toys", "price": 399, "image": "images/toy.jpg"},
]

@app.route("/")
def home():
    return render_template("home.html", products=products)

# 🔥 DYNAMIC PAYMENT ROUTE
@app.route("/payment/<string:name>/<int:price>")
def payment(name, price):
    return render_template("payment.html", name=name, price=price)

if __name__ == "__main__":
    app.run(debug=True)
    
@app.route("/add_to_cart/<name>/<int:price>")
def add_to_cart(name, price):
    cart.append({"name": name, "price": price})
    return redirect("/cart")

@app.route("/cart")
def view_cart():
    total = sum(item["price"] for item in cart)
    return render_template("cart.html", cart=cart, total=total)

@app.route("/payment", methods=["GET", "POST"])
def payment():
    if request.method == "POST":
        name = request.form["name"]
        amount = request.form["amount"]
        return f"Payment Successful! {name} paid ₹{amount}"
    return render_template("payment.html")

if __name__ == "__main__":
    app.run(debug=True)
    