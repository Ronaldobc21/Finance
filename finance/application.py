from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

import datetime

# Configure application
app = Flask(__name__)

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"

    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    users = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])
    stocks = db.execute(
        "SELECT symbol, SUM(shares) as total FROM transactions WHERE user_id = :user_id GROUP BY symbol HAVING total > 0", user_id=session["user_id"])
    quotes = {}
    cash = users[0]["cash"]
    total = cash

    for stock in stocks:
        quotes[stock["symbol"]] = lookup(stock["symbol"])
        total += lookup(stock["symbol"])["price"]*stock["total"]

    total = float(total)

    quotes["total"] = 0

    return render_template("index.html", quotes=quotes, stocks=stocks, total=total, cash=cash)

    """Show portfolio of stocks"""


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide symbol", 400)

        if not request.form.get("shares"):
            return apology("must provide shares", 400)

        symbol = lookup(request.form.get("symbol"))

        if not symbol:
            return apology("Symbol not found", 400)

        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("shares must be a positive integer", 400)

        if shares <= 0:
            return apology("can not buy less than or 0 shares", 400)

        users = db.execute("SELECT cash FROM users WHERE id = :user", user=session["user_id"])

        cash = users[0]["cash"]
        price = float(symbol["price"])
        total = float(shares * symbol["price"])

        if total > cash:
            return apology("Have not money enougt", 400)

        transactions = db.execute("UPDATE users SET cash = cash - :price WHERE id = :user_id",
                                  price=total, user_id=session["user_id"])

        transactions = db.execute("INSERT INTO transactions (symbol, user_id, shares, price, timestamp)  VALUES(:symbol, :user_id, :shares, :price, :timestamp)",
                                  user_id=session["user_id"], symbol=request.form.get("symbol"), shares=request.form.get("shares"), price=symbol["price"], timestamp=datetime.datetime.now())

        flash("Bought")
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():

    transactions = db.execute(
        "SELECT symbol, shares, price, timestamp FROM transactions WHERE user_id = :id ORDER BY timestamp ASC ", id=session["user_id"])
    # print(transactions)
    return render_template("history.html", transactions=transactions)

    # SELECT symbol, shares, price, timestamp FROM transactions WHERE user_id='2' order by timestamp ASC
    # return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Must provide Symbol", 400)

        symbol = request.form.get("symbol")

        response = lookup(symbol)

        if not response:
            return apology("Symbol not found", 400)

        return render_template("quoted.html", info=response)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Must provide Username", 400)
        if not request.form.get("password"):
            return apology("Must provide password", 400)
        if not request.form.get("confirmation"):
            return apology("Must provide confirmation", 400)

        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("password does't match", 400)

        if len(db.execute("SELECT * FROM users WHERE username= :username", username=request.form.get("username"))) != 0:
            return apology("username taken :D", 400)

        password = generate_password_hash(request.form.get("password"))

        newUser = db.execute("INSERT INTO users(username, hash) VALUES(:user, :passw) ",
                             user=request.form.get("username"), passw=password)

        flash("Registered!")

        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide symbol", 400)

        if not request.form.get("shares"):
            return apology("must provide shares", 400)

        symbol = lookup(request.form.get("symbol"))

        if not symbol:
            return apology("Symbol not found", 400)

        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("shares must be a positive integer", 400)

        if shares <= 0:
            return apology("can not buy less than or 0 shares", 400)

        users = db.execute("SELECT cash FROM users WHERE id = :user", user=session["user_id"])
        cash = float(users[0]["cash"])

        shares = int(request.form.get("shares"))
        total = float(shares * symbol["price"])

        stocks = db.execute("SELECT symbol, SUM(shares) as total from transactions WHERE user_id = :user_id AND symbol = :symbol group by symbol",
                            user_id=session["user_id"], symbol=request.form.get("symbol"))

        if len(stocks) != 1 or stocks[0]["total"] < shares:
            return apology("Don't Have more buys", 400)

        # SELECT SUM(shares) as total from transactions where user_id='2'
        # SELECT symbol,SUM(shares) as total from transactions where user_id='2' group by symbol

        if total > cash:
            return apology("Have not money enougt", 400)
        transactions = db.execute("UPDATE users SET cash = cash + :price WHERE id = :user_id",
                                  price=total, user_id=session["user_id"])

        transactions = db.execute("INSERT INTO transactions (symbol, user_id, shares, price, timestamp)  VALUES(:symbol, :user_id, :shares, :price, :timestamp)",
                                  user_id=session["user_id"], symbol=request.form.get("symbol"), shares=-shares, price=symbol["price"], timestamp=datetime.datetime.now())

        flash("Sold")
        return redirect("/")

    else:
        stocks = db.execute(
            "SELECT symbol,SUM(shares) as total from transactions WHERE user_id = :user_id group by symbol having total > 0", user_id=session["user_id"])
        return render_template("sell.html", stocks=stocks)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
