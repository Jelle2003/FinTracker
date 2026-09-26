from flask import Flask, render_template, request, url_for, flash, redirect, Response
from datetime import date, datetime, date as dt_date
import os
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from sqlalchemy import func
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from .database import db
from .models import User, Expense, Income, Investment


app = Flask(
    __name__,
    template_folder="../../frontend"
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expenses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "my-secret-key"

db.init_app(app)


# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access FINTRACK."
login_manager.login_message_category = "error"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Create database tables
with app.app_context():
    db.create_all()


CATEGORIES = [
    "Food",
    "Transport",
    "Rent",
    "Utilities",
    "Health"
]

INCOME_CATEGORIES = [
    "Salary",
    "DJ income",
    "Refund",
    "Other"
]


def parse_date_or_none(s: str):
    if not s:
        return None

    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            flash("Please enter your username and password.", "error")
            return render_template("login.html")

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        login_user(user)

        flash("Welcome back!", "success")

        next_page = request.args.get("next")

        if next_page and next_page.startswith("/"):
            return redirect(next_page)

        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been logged out.", "success")

    return redirect(url_for("login"))


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
@login_required
def index():
    year_str = (request.args.get("year") or str(date.today().year)).strip()
    try:
        selected_year = int(year_str)
        if selected_year < 1900 or selected_year > 2100:
            raise ValueError
    except ValueError:
        selected_year = date.today().year

    year_start = date(selected_year, 1, 1)
    year_end = date(selected_year, 12, 31)

    expense_total = db.session.query(func.sum(Expense.amount)).filter(
        Expense.date >= year_start, Expense.date <= year_end
    ).scalar() or 0

    income_total = db.session.query(func.sum(Income.amount)).filter(
        Income.start_date >= year_start, Income.start_date <= year_end
    ).scalar() or 0

    monthly_income = dict(db.session.query(
        func.strftime("%m", Income.start_date), func.sum(Income.amount)
    ).filter(
        Income.start_date >= year_start, Income.start_date <= year_end
    ).group_by(func.strftime("%m", Income.start_date)).all())

    monthly_expenses = dict(db.session.query(
        func.strftime("%m", Expense.date), func.sum(Expense.amount)
    ).filter(
        Expense.date >= year_start, Expense.date <= year_end
    ).group_by(func.strftime("%m", Expense.date)).all())

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    income_values = [round(float(monthly_income.get(f"{m:02d}", 0) or 0), 2) for m in range(1, 13)]
    expense_values = [round(float(monthly_expenses.get(f"{m:02d}", 0) or 0), 2) for m in range(1, 13)]

    category_rows = db.session.query(
        Expense.category, func.sum(Expense.amount)
    ).filter(
        Expense.date >= year_start, Expense.date <= year_end
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

    recent_expenses = Expense.query.order_by(Expense.date.desc(), Expense.id.desc()).limit(5).all()
    recent_incomes = Income.query.order_by(Income.start_date.desc(), Income.id.desc()).limit(5).all()

    income_total = round(float(income_total), 2)
    expense_total = round(float(expense_total), 2)
    balance = round(income_total - expense_total, 2)
    savings_rate = round((balance / income_total) * 100, 1) if income_total else 0

    years = {date.today().year}
    years.update(y for (y,) in db.session.query(func.strftime("%Y", Expense.date)).distinct().all() if y)
    years.update(y for (y,) in db.session.query(func.strftime("%Y", Income.start_date)).distinct().all() if y)
    years = sorted({int(y) for y in years} | {selected_year}, reverse=True)

    return render_template(
        "index.html", selected_year=selected_year, years=years,
        income_total=income_total, expense_total=expense_total,
        balance=balance, savings_rate=savings_rate,
        month_names=month_names, income_values=income_values,
        expense_values=expense_values,
        category_labels=[c for c, _ in category_rows],
        category_values=[round(float(v or 0), 2) for _, v in category_rows],
        recent_expenses=recent_expenses, recent_incomes=recent_incomes
    )


@app.route("/expenses")
@login_required
def expenses():
    start_str = (request.args.get("start") or "").strip()
    end_str = (request.args.get("end") or "").strip()
    selected_category = (request.args.get("category") or "").strip()
    start_date = parse_date_or_none(start_str)
    end_date = parse_date_or_none(end_str)

    if start_date and end_date and end_date < start_date:
        flash("End date cannot be before start date", "error")
        start_date = end_date = None
        start_str = end_str = ""

    q = Expense.query
    if start_date:
        q = q.filter(Expense.date >= start_date)
    if end_date:
        q = q.filter(Expense.date <= end_date)
    if selected_category:
        q = q.filter(Expense.category == selected_category)
    expenses = q.order_by(Expense.date.desc(), Expense.id.desc()).all()
    total = round(sum(e.amount for e in expenses), 2)

    cat_q = db.session.query(Expense.category, func.sum(Expense.amount))
    day_q = db.session.query(Expense.date, func.sum(Expense.amount))
    cat_rows = cat_q.filter(*([Expense.date >= start_date] if start_date else []),
                            *([Expense.date <= end_date] if end_date else []),
                            *([Expense.category == selected_category] if selected_category else [])).group_by(Expense.category).all()
    day_rows = day_q.filter(*([Expense.date >= start_date] if start_date else []),
                            *([Expense.date <= end_date] if end_date else []),
                            *([Expense.category == selected_category] if selected_category else [])).group_by(Expense.date).order_by(Expense.date).all()
    return render_template("expenses.html", categories=CATEGORIES,
        today=date.today().isoformat(), expenses=expenses, total=total,
        start_str=start_str, end_str=end_str, selected_category=selected_category,
        cat_labels=[c for c, _ in cat_rows], cat_values=[round(float(v or 0), 2) for _, v in cat_rows],
        day_labels=[d.isoformat() for d, _ in day_rows], day_values=[round(float(v or 0), 2) for _, v in day_rows])


# ============================================================
# ADD EXPENSE
# ============================================================

@app.route("/expenses/add", methods=["POST"])
@login_required
def add():

    description = (
        request.form.get("description") or ""
    ).strip()

    amount_str = (
        request.form.get("amount") or ""
    ).strip()

    category = (
        request.form.get("category") or ""
    ).strip()

    date_str = (
        request.form.get("date") or ""
    ).strip()

    if not description or not amount_str or not category:
        flash(
            "Please fill description, amount and category",
            "error"
        )

        return redirect(url_for("index"))

    try:
        amount = float(amount_str)

        if amount <= 0:
            raise ValueError

    except ValueError:
        flash(
            "Amount must be a positive number",
            "error"
        )

        return redirect(url_for("index"))

    try:
        d = (
            datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).date()
            if date_str
            else date.today()
        )

    except ValueError:
        d = date.today()

    expense = Expense(
        description=description,
        amount=amount,
        category=category,
        date=d
    )

    db.session.add(expense)
    db.session.commit()

    flash("Expense added", "success")

    return redirect(url_for("index"))


# ============================================================
# DELETE EXPENSE
# ============================================================

@app.route("/expenses/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete(expense_id):

    expense = Expense.query.get_or_404(expense_id)

    db.session.delete(expense)
    db.session.commit()

    flash("Expense deleted", "success")

    return redirect(url_for("index"))


# ============================================================
# EDIT EXPENSE
# ============================================================

@app.route("/expenses/edit/<int:expense_id>", methods=["GET"])
@login_required
def edit(expense_id):

    expense = Expense.query.get_or_404(expense_id)

    return render_template(
        "edit.html",
        expense=expense,
        categories=CATEGORIES,
        today=dt_date.today().isoformat()
    )


@app.route("/expenses/edit/<int:expense_id>", methods=["POST"])
@login_required
def edit_post(expense_id):

    expense = Expense.query.get_or_404(expense_id)

    description = (
        request.form.get("description") or ""
    ).strip()

    amount_str = (
        request.form.get("amount") or ""
    ).strip()

    category = (
        request.form.get("category") or ""
    ).strip()

    date_str = (
        request.form.get("date") or ""
    ).strip()

    if not description or not amount_str or not category:
        flash(
            "Please fill description, amount and category",
            "error"
        )

        return redirect(
            url_for(
                "edit",
                expense_id=expense_id
            )
        )

    try:
        amount = float(amount_str)

        if amount <= 0:
            raise ValueError

    except ValueError:
        flash(
            "Amount must be a positive number",
            "error"
        )

        return redirect(
            url_for(
                "edit",
                expense_id=expense_id
            )
        )

    try:
        d = (
            datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).date()
            if date_str
            else dt_date.today()
        )

    except ValueError:
        d = dt_date.today()

    expense.description = description
    expense.amount = amount
    expense.category = category
    expense.date = d

    db.session.commit()

    flash("Expense updated", "success")

    return redirect(url_for("index"))



# ============================================================
# INCOME
# ============================================================

@app.route("/income")
@login_required
def income():
    incomes = Income.query.order_by(
        Income.start_date.desc(),
        Income.id.desc()
    ).all()

    total = round(sum(i.amount for i in incomes), 2)

    month_expression = func.strftime("%Y-%m", Income.start_date)
    month_rows = db.session.query(
        month_expression,
        func.sum(Income.amount)
    ).group_by(
        month_expression
    ).order_by(
        month_expression
    ).all()

    month_labels = [month for month, _ in month_rows]
    month_values = [round(float(amount or 0), 2) for _, amount in month_rows]

    return render_template(
        "income.html",
        incomes=incomes,
        total=total,
        categories=INCOME_CATEGORIES,
        month_labels=month_labels,
        month_values=month_values
    )


@app.route("/income/add", methods=["POST"])
@login_required
def add_income():
    description = (request.form.get("description") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()
    category = (request.form.get("category") or "").strip()
    start_str = (request.form.get("start_date") or "").strip()
    end_str = (request.form.get("end_date") or "").strip()

    if not description or not amount_str or not category or not start_str or not end_str:
        flash("Please fill in all income fields.", "error")
        return redirect(url_for("income"))

    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number.", "error")
        return redirect(url_for("income"))

    start_date = parse_date_or_none(start_str)
    end_date = parse_date_or_none(end_str)

    if not start_date or not end_date:
        flash("Please enter valid start and end dates.", "error")
        return redirect(url_for("income"))

    if end_date < start_date:
        flash("End date cannot be before start date.", "error")
        return redirect(url_for("income"))

    income_item = Income(
        description=description,
        amount=amount,
        category=category,
        start_date=start_date,
        end_date=end_date
    )

    db.session.add(income_item)
    db.session.commit()

    flash("Income added.", "success")
    return redirect(url_for("income"))


@app.route("/income/delete/<int:income_id>", methods=["POST"])
@login_required
def delete_income(income_id):
    income_item = Income.query.get_or_404(income_id)

    db.session.delete(income_item)
    db.session.commit()

    flash("Income deleted.", "success")
    return redirect(url_for("income"))


@app.route("/income/edit/<int:income_id>", methods=["GET"])
@login_required
def edit_income(income_id):
    income_item = Income.query.get_or_404(income_id)

    return render_template(
        "income_edit.html",
        income=income_item,
        categories=INCOME_CATEGORIES
    )


@app.route("/income/edit/<int:income_id>", methods=["POST"])
@login_required
def edit_income_post(income_id):
    income_item = Income.query.get_or_404(income_id)

    description = (request.form.get("description") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()
    category = (request.form.get("category") or "").strip()
    start_str = (request.form.get("start_date") or "").strip()
    end_str = (request.form.get("end_date") or "").strip()

    if not description or not amount_str or not category or not start_str or not end_str:
        flash("Please fill in all income fields.", "error")
        return redirect(url_for("edit_income", income_id=income_id))

    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number.", "error")
        return redirect(url_for("edit_income", income_id=income_id))

    start_date = parse_date_or_none(start_str)
    end_date = parse_date_or_none(end_str)

    if not start_date or not end_date:
        flash("Please enter valid start and end dates.", "error")
        return redirect(url_for("edit_income", income_id=income_id))

    if end_date < start_date:
        flash("End date cannot be before start date.", "error")
        return redirect(url_for("edit_income", income_id=income_id))

    income_item.description = description
    income_item.amount = amount
    income_item.category = category
    income_item.start_date = start_date
    income_item.end_date = end_date

    db.session.commit()

    flash("Income updated.", "success")
    return redirect(url_for("income"))



# ============================================================
# INVESTING / MARKET DATA
# ============================================================

def fetch_url(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FINTRACK/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception:
        return None


def market_price(symbol):
    encoded = urllib.parse.quote(symbol.strip().upper(), safe="")
    data = fetch_url(f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=1d&interval=1d")
    if not data:
        return None
    try:
        payload = json.loads(data)
        result = payload["chart"]["result"][0]
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice")
        currency = meta.get("currency", "")
        return {"price": float(price), "currency": currency} if price is not None else None
    except Exception:
        return None


def market_news(topic=None):
    base_query = "beleggen OR ETF OR aandelen OR crypto OR economie"
    if topic:
        clean_topic = " ".join(topic.split())[:120]
        base_query = f"{base_query} {clean_topic}"
    query = urllib.parse.quote(base_query)
    data = fetch_url(
        f"https://news.google.com/rss/search?q={query}&hl=nl-BE&gl=BE&ceid=BE:nl"
    )
    if not data:
        return []
    try:
        root = ET.fromstring(data)
        items = []
        for item in root.findall("./channel/item")[:12]:
            items.append({
                "title": item.findtext("title") or "",
                "link": item.findtext("link") or "",
                "published": item.findtext("pubDate") or "",
                "source": item.findtext("source") or ""
            })
        return items
    except Exception:
        return []


def market_snapshot(symbols=None):
    default_symbols = [
        ("^GSPC", "S&P 500"),
        ("^IXIC", "Nasdaq"),
        ("^STOXX50E", "Euro Stoxx 50"),
        ("^BFX", "BEL 20"),
        ("BTC-USD", "Bitcoin"),
        ("ETH-USD", "Ethereum"),
        ("EURUSD=X", "EUR/USD"),
        ("GC=F", "Goud"),
        ("CL=F", "Olie")
    ]
    requested = symbols or [symbol for symbol, _ in default_symbols]
    names = dict(default_symbols)
    result = []
    for symbol in requested:
        quote = market_price(symbol)
        if quote:
            result.append({
                "symbol": symbol,
                "name": names.get(symbol, symbol),
                "price": quote["price"],
                "currency": quote["currency"]
            })
    return result


def ollama_chat(prompt, model=None):
    model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    payload = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Je bent FINTRACK AI, een Nederlandstalige financiële "
                    "onderzoeksassistent. Gebruik actuele marktdata en nieuws "
                    "als primaire context. Geef geen gegarandeerde rendementen "
                    "en presenteer geen koop/verkoopbeslissing als zekerheid. "
                    "Maak duidelijk onderscheid tussen feiten, interpretatie "
                    "en onzekerheid. Geef bij financiële vragen altijd risico's, "
                    "aannames en relevante Belgische aandachtspunten. "
                    "Verzin geen actuele cijfers die niet in de aangeleverde data staan."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 2048, "num_predict": 400},
        "keep_alive": "10m"
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=600) as response:
        result = json.loads(response.read())

    return (result.get("message") or {}).get("content", "").strip()


@app.route("/investing")
@login_required
def investing():
    holdings = Investment.query.order_by(Investment.symbol).all()
    rows = []
    total_cost = 0.0
    total_value = 0.0
    all_prices = True
    for h in holdings:
        cost = h.quantity * h.average_price
        quote = market_price(h.symbol)
        current_price = quote["price"] if quote else None
        value = h.quantity * current_price if current_price is not None else None
        total_cost += cost
        if value is not None:
            total_value += value
        else:
            all_prices = False
        rows.append({"holding": h, "cost": cost, "current_price": current_price,
                     "value": value, "currency": quote["currency"] if quote else ""})
    gain = total_value - total_cost if holdings and all_prices else None
    return render_template("investing.html", rows=rows, total_cost=total_cost,
                           total_value=total_value, gain=gain)


@app.route("/investing/add", methods=["POST"])
@login_required
def add_investment():
    symbol = (request.form.get("symbol") or "").strip().upper()
    name = (request.form.get("name") or symbol).strip()
    asset_type = (request.form.get("asset_type") or "ETF").strip()
    try:
        quantity = float(request.form.get("quantity") or 0)
        average_price = float(request.form.get("average_price") or 0)
        if not symbol or quantity <= 0 or average_price < 0:
            raise ValueError
    except ValueError:
        flash("Vul een geldig symbool, aantal en aankoopprijs in.", "error")
        return redirect(url_for("investing"))
    db.session.add(Investment(symbol=symbol, name=name, asset_type=asset_type,
                              quantity=quantity, average_price=average_price))
    db.session.commit()
    flash("Belegging toegevoegd.", "success")
    return redirect(url_for("investing"))


@app.route("/investing/delete/<int:investment_id>", methods=["POST"])
@login_required
def delete_investment(investment_id):
    item = Investment.query.get_or_404(investment_id)
    db.session.delete(item)
    db.session.commit()
    flash("Belegging verwijderd.", "success")
    return redirect(url_for("investing"))


@app.route("/market")
@login_required
def market():
    return render_template("market.html", news=market_news())


@app.route("/ai-investor", methods=["GET", "POST"])
@login_required
def ai_investor():
    answer = None
    question = ""

    if request.method == "POST":
        question = (request.form.get("question") or "").strip()

        if not question:
            flash("Stel eerst een vraag.", "error")
        else:
            holdings = Investment.query.all()
            portfolio = []
            holding_symbols = []

            for h in holdings:
                quote = market_price(h.symbol)
                portfolio.append({
                    "symbol": h.symbol,
                    "name": h.name,
                    "type": h.asset_type,
                    "quantity": h.quantity,
                    "average_price": h.average_price,
                    "current_price": quote["price"] if quote else None,
                    "currency": quote["currency"] if quote else ""
                })
                holding_symbols.append(h.symbol)

            market_data = market_snapshot()
            for item in portfolio:
                if item["current_price"] is not None:
                    market_data.append({
                        "symbol": item["symbol"],
                        "name": item["name"],
                        "price": item["current_price"],
                        "currency": item["currency"]
                    })

            news = market_news(question)[:5]

            prompt = (
                f"VANDAAG: {date.today().isoformat()}\n\n"
                f"VRAAG VAN DE GEBRUIKER:\n{question}\n\n"
                f"ACTUELE MARKTDATA:\n{json.dumps(market_data, ensure_ascii=False)}\n\n"
                f"ACTUEEL NIEUWS:\n{json.dumps(news, ensure_ascii=False)}\n\n"
                f"PORTFOLIO VAN DE GEBRUIKER:\n{json.dumps(portfolio, ensure_ascii=False)}\n\n"
                "Beantwoord de vraag concreet in het Nederlands. "
                "Gebruik de actuele data en nieuwsitems hierboven. "
                "Als informatie ontbreekt, zeg dat expliciet. "
                "Als de gebruiker om aandelen, ETF's of crypto vraagt, "
                "vergelijk relevante opties in plaats van blind één keuze te geven. "
                "Vermeld bij actuele cijfers altijd dat het moment van ophalen relevant is."
            )

            try:
                answer = ollama_chat(prompt)
                if not answer:
                    flash("De lokale AI gaf geen antwoord terug.", "error")
            except urllib.error.URLError:
                flash(
                    "De lokale AI is niet bereikbaar. Controleer of Ollama draait "
                    "en of het model qwen2.5:3b-instruct is geïnstalleerd.",
                    "error"
                )
            except Exception as exc:
                flash(f"AI-aanvraag mislukt: {exc}", "error")

    return render_template("ai_investor.html", answer=answer, question=question)



