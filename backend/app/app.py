from flask import Flask, render_template, request, url_for, flash, redirect, Response, session, g
from datetime import date, datetime, timedelta
import os
import json
import secrets
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from sqlalchemy import func, inspect, text
from sqlalchemy.exc import IntegrityError
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from google import genai

from .database import db
from .models import User, Expense, Income, Investment


app = Flask(
    __name__,
    template_folder="../../frontend",
    static_folder="../../frontend/css",
    static_url_path="/css"
)

# Security configuration. The secret is deliberately required from the
# environment so it can never be accidentally committed to GitHub.
secret_key = os.environ.get("FINTRACK_SECRET_KEY")
if not secret_key or len(secret_key) < 32:
    raise RuntimeError(
        "FINTRACK_SECRET_KEY must be set to a random value of at least 32 characters."
    )

trusted_hosts = [
    host.strip()
    for host in os.environ.get(
        "FINTRACK_TRUSTED_HOSTS",
        "fintrackerjelle.duckdns.org,localhost,127.0.0.1"
    ).split(",")
    if host.strip()
]

app.config.update(
    SQLALCHEMY_DATABASE_URI="sqlite:///expenses.db",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=secret_key,
    TRUSTED_HOSTS=trusted_hosts,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    REMEMBER_COOKIE_SECURE=True,
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=1800,
    SESSION_REFRESH_EACH_REQUEST=True,
    MAX_CONTENT_LENGTH=1 * 1024 * 1024,
    MAX_FORM_MEMORY_SIZE=500_000,
    MAX_FORM_PARTS=100,
)

# nginx terminates HTTPS before forwarding the request to Gunicorn.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Generate the CSP nonce before Flask-WTF registers its CSRF before-request
# handler. That way even a CSRF-rejected request still has a nonce available
# when the after-request security headers are generated.
@app.before_request
def prepare_csp_nonce():
    g.csp_nonce = secrets.token_urlsafe(32)


csrf = CSRFProtect(app)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=os.environ.get("FINTRACK_RATE_LIMIT_STORAGE", "memory://"),
)


@app.after_request
def add_security_headers(response):
    """Add browser-side security controls to every response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https: data:; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        f"script-src 'self' 'nonce-{g.csp_nonce}' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
        "connect-src 'self'; "
    )
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


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


# Maak de tabellen aan en voer kleine migraties uit voor oudere databases.
# Bestaande gegevens blijven gekoppeld aan de eerste gebruiker.
with app.app_context():
    db.create_all()

    with db.engine.begin() as connection:
        for table in ("expense", "income", "investment"):
            columns = {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")}
            if "user_id" not in columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES user(id)"
                )

        user_columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(user)")
        }
        if "is_admin" not in user_columns:
            connection.exec_driver_sql(
                "ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"
            )

        user_profile_columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(user)")
        }
        if "display_name" not in user_profile_columns:
            connection.exec_driver_sql("ALTER TABLE user ADD COLUMN display_name VARCHAR(80)")
        if "email" not in user_profile_columns:
            connection.exec_driver_sql("ALTER TABLE user ADD COLUMN email VARCHAR(254)")
        if "currency" not in user_profile_columns:
            connection.exec_driver_sql("ALTER TABLE user ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'EUR'")
        if "avatar_color" not in user_profile_columns:
            connection.exec_driver_sql("ALTER TABLE user ADD COLUMN avatar_color VARCHAR(20) NOT NULL DEFAULT 'blue'")

        first_user = connection.exec_driver_sql(
            "SELECT id FROM user ORDER BY id LIMIT 1"
        ).fetchone()

        if first_user:
            for table in ("expense", "income", "investment"):
                connection.exec_driver_sql(
                    f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL",
                    (first_user[0],)
                )

            admin_exists = connection.exec_driver_sql(
                "SELECT 1 FROM user WHERE is_admin = 1 LIMIT 1"
            ).fetchone()
            if not admin_exists:
                connection.exec_driver_sql(
                    "UPDATE user SET is_admin = 1 WHERE id = ?",
                    (first_user[0],)
                )


def exchange_rate(from_currency, to_currency):
    """Get the current exchange rate. Financial data stays stored in EUR."""
    from_currency = (from_currency or "EUR").upper()
    to_currency = (to_currency or "EUR").upper()
    if from_currency == to_currency:
        return 1.0
    cache = getattr(g, "_fx_cache", {})
    cache_key = f"{from_currency}:{to_currency}"
    if cache_key in cache:
        return cache[cache_key]
    if from_currency == "EUR":
        quote = market_price(f"EUR{to_currency}=X")
        rate = quote["price"] if quote else None
        cache[cache_key] = rate
        g._fx_cache = cache
        return rate
    if to_currency == "EUR":
        rate = exchange_rate("EUR", from_currency)
        return (1 / rate) if rate else None
    to_eur = exchange_rate(from_currency, "EUR")
    eur_to_target = exchange_rate("EUR", to_currency)
    rate = to_eur * eur_to_target if to_eur and eur_to_target else None
    cache[cache_key] = rate
    g._fx_cache = cache
    return rate


def convert_amount(amount, from_currency, to_currency):
    rate = exchange_rate(from_currency, to_currency)
    return amount * rate if rate is not None else None


# Add the investment currency to older databases.
with app.app_context():
    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("investment")}
    if "currency" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE investment ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'EUR'"))


def currency_info():
    """Return the currency chosen by the logged-in user."""
    code = getattr(current_user, "currency", "EUR") if current_user.is_authenticated else "EUR"
    return {
        "currency_code": code,
        "currency_symbol": {"EUR": "€", "USD": "$", "GBP": "£"}.get(code, "€"),
    }


def money(value, from_currency="EUR"):
    """Format an amount in the currency selected by the user."""
    converted = convert_amount(float(value or 0), from_currency, current_user.currency)
    if converted is None:
        converted = float(value or 0)
    symbol = currency_info()["currency_symbol"]
    return f"{symbol}{converted:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def money_value(value, from_currency="EUR"):
    """Return a converted number for form fields and charts."""
    converted = convert_amount(float(value or 0), from_currency, current_user.currency)
    return round(converted if converted is not None else float(value or 0), 2)


@app.context_processor
def inject_currency():
    return currency_info()


def owned_query(model):
    """Return only records owned by the logged-in user."""
    return model.query.filter(model.user_id == current_user.id)


def owned_or_404(model, record_id):
    """Fetch a record only when it belongs to the logged-in user."""
    return model.query.filter(
        model.id == record_id,
        model.user_id == current_user.id
    ).first_or_404()


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


def safe_external_url(value: str):
    """Allow only absolute HTTP(S) URLs from external content."""
    parsed = urllib.parse.urlparse((value or "").strip())
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value.strip()
    return ""


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
@limiter.limit("5 per minute", methods=["POST"])
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
        parsed_next = urllib.parse.urlparse(next_page or "")

        # Alleen lokale redirects zijn toegestaan; externe URLs worden geblokkeerd.
        if (
            next_page
            and parsed_next.scheme == ""
            and parsed_next.netloc == ""
            and parsed_next.path.startswith("/")
        ):
            return redirect(next_page)

        return redirect(url_for("index"))

    return render_template("login.html")



@app.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    username = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if len(username) < 3 or len(username) > 80:
            flash("Kies een gebruikersnaam van 3 tot 80 tekens.", "error")
            return render_template("register.html", username=username)
        if len(password) < 12:
            flash("Gebruik een wachtwoord van minstens 12 tekens.", "error")
            return render_template("register.html", username=username)
        if len(password) > 128:
            flash("Gebruik een wachtwoord van maximaal 128 tekens.", "error")
            return render_template("register.html", username=username)
        if password != confirm_password:
            flash("De wachtwoorden komen niet overeen.", "error")
            return render_template("register.html", username=username)
        if User.query.filter_by(username=username).first():
            flash("Deze gebruikersnaam is al in gebruik.", "error")
            return render_template("register.html", username=username)

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Deze gebruikersnaam is al in gebruik. Kies een andere.", "error")
            return render_template("register.html", username=username)

        login_user(user)
        flash("Je account is aangemaakt. Welkom bij FINTRACK!", "success")
        return redirect(url_for("index"))

    return render_template("register.html", username=username)

@app.route("/account", methods=["GET", "POST"])
@login_required
@limiter.limit("5 per minute", methods=["POST"])
def account():
    user = db.session.get(User, current_user.id)

    if request.method == "POST":
        action = request.form.get("action", "profile")

        if action == "profile":
            display_name = (request.form.get("display_name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            currency = (request.form.get("currency") or "EUR").upper()
            avatar_color = (request.form.get("avatar_color") or "blue").lower()

            if len(display_name) > 80:
                flash("Je weergavenaam mag maximaal 80 tekens bevatten.", "error")
                return render_template("account.html", user=user)

            if len(email) > 254 or (email and ("@" not in email or "." not in email.rsplit("@", 1)[-1])):
                flash("Vul een geldig e-mailadres in of laat het veld leeg.", "error")
                return render_template("account.html", user=user)

            if currency not in {"EUR", "USD", "GBP"}:
                flash("Ongeldige valuta.", "error")
                return render_template("account.html", user=user)

            if avatar_color not in {"blue", "purple", "green", "orange", "pink"}:
                flash("Ongeldige profielkleur.", "error")
                return render_template("account.html", user=user)

            user.display_name = display_name or None
            user.email = email or None
            user.currency = currency
            user.avatar_color = avatar_color
            db.session.commit()
            flash("Je profiel is bijgewerkt.", "success")
            return redirect(url_for("account"))

        if action == "password":
            current_password = request.form.get("current_password") or ""
            new_password = request.form.get("new_password") or ""
            confirm_password = request.form.get("confirm_password") or ""

            if not user.check_password(current_password):
                flash("Je huidige wachtwoord is niet correct.", "error")
                return render_template("account.html", user=user)

            if len(new_password) < 12 or len(new_password) > 128:
                flash("Gebruik een nieuw wachtwoord van 12 tot 128 tekens.", "error")
                return render_template("account.html", user=user)

            if new_password != confirm_password:
                flash("De nieuwe wachtwoorden komen niet overeen.", "error")
                return render_template("account.html", user=user)

            if new_password == current_password:
                flash("Kies een nieuw wachtwoord dat verschilt van je huidige wachtwoord.", "error")
                return render_template("account.html", user=user)

            user.set_password(new_password)
            db.session.commit()

            # Rotate the authenticated session after a credential change.
            logout_user()
            session.clear()
            login_user(user)

            flash("Je wachtwoord is succesvol gewijzigd.", "success")
            return redirect(url_for("account"))

        flash("Ongeldige accountactie.", "error")
        return redirect(url_for("account"))

    return render_template("account.html", user=user)


def admin_required(view):
    """Allow access only to authenticated FINTRACK administrators."""
    from functools import wraps

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            return Response("Forbidden", status=403)
        return view(*args, **kwargs)

    return wrapped


@app.route("/admin")
@admin_required
def admin():
    users = User.query.order_by(User.username.asc()).all()
    total_users = len(users)
    total_expenses = Expense.query.count()
    total_incomes = Income.query.count()
    total_investments = Investment.query.count()
    admin_count = User.query.filter_by(is_admin=True).count()

    return render_template(
        "admin.html",
        users=users,
        total_users=total_users,
        total_expenses=total_expenses,
        total_incomes=total_incomes,
        total_investments=total_investments,
        admin_count=admin_count,
    )


@app.route("/admin/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        flash("Gebruiker niet gevonden.", "error")
        return redirect(url_for("admin"))

    if user.id == current_user.id:
        flash("Je kunt je eigen adminrechten niet wijzigen.", "error")
        return redirect(url_for("admin"))

    if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash("Er moet altijd minstens één administrator overblijven.", "error")
        return redirect(url_for("admin"))

    user.is_admin = not user.is_admin
    db.session.commit()
    flash(
        f"Adminrechten voor {user.username} zijn " +
        ("ingeschakeld." if user.is_admin else "uitgeschakeld."),
        "success",
    )
    return redirect(url_for("admin"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        flash("Gebruiker niet gevonden.", "error")
        return redirect(url_for("admin"))

    if user.id == current_user.id:
        flash("Je kunt je eigen account niet verwijderen vanuit het adminpaneel.", "error")
        return redirect(url_for("admin"))

    if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash("De laatste administrator kan niet worden verwijderd.", "error")
        return redirect(url_for("admin"))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"Gebruiker {username} is verwijderd.", "success")
    return redirect(url_for("admin"))


@app.route("/logout", methods=["POST"])
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
        Expense.user_id == current_user.id, Expense.date >= year_start, Expense.date <= year_end
    ).scalar() or 0

    income_total = db.session.query(func.sum(Income.amount)).filter(
        Income.user_id == current_user.id, Income.start_date >= year_start, Income.start_date <= year_end
    ).scalar() or 0

    monthly_income = dict(db.session.query(
        func.strftime("%m", Income.start_date), func.sum(Income.amount)
    ).filter(
        Income.user_id == current_user.id, Income.start_date >= year_start, Income.start_date <= year_end
    ).group_by(func.strftime("%m", Income.start_date)).all())

    monthly_expenses = dict(db.session.query(
        func.strftime("%m", Expense.date), func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id, Expense.date >= year_start, Expense.date <= year_end
    ).group_by(func.strftime("%m", Expense.date)).all())

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    income_values = [round(float(monthly_income.get(f"{m:02d}", 0) or 0), 2) for m in range(1, 13)]
    expense_values = [round(float(monthly_expenses.get(f"{m:02d}", 0) or 0), 2) for m in range(1, 13)]

    category_rows = db.session.query(
        Expense.category, func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id, Expense.date >= year_start, Expense.date <= year_end
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

    recent_expenses = owned_query(Expense).order_by(Expense.date.desc(), Expense.id.desc()).limit(5).all()
    recent_incomes = owned_query(Income).order_by(Income.start_date.desc(), Income.id.desc()).limit(5).all()

    # --------------------------------------------------------
    # Beleggingssamenvatting
    # De dashboardcijfers komen rechtstreeks uit dezelfde
    # Investment-tabel als de pagina "Beleggen".
    # --------------------------------------------------------
    investments = owned_query(Investment).order_by(Investment.name.asc()).all()
    investment_rows = []
    investment_total_cost = 0.0
    investment_market_value = 0.0
    priced_investments = 0

    for investment in investments:
        quantity = float(investment.quantity or 0)
        average_price = float(investment.average_price or 0)
        cost = quantity * average_price
        quote = market_price(investment.symbol)

        current_price = quote["price"] if quote else None
        current_value = quantity * current_price if current_price is not None else None

        investment_total_cost += cost
        if current_value is not None:
            investment_market_value += current_value
            priced_investments += 1

        gain = (current_value - cost) if current_value is not None else None
        gain_pct = ((gain / cost) * 100) if gain is not None and cost else None

        investment_rows.append({
            "id": investment.id,
            "symbol": investment.symbol,
            "name": investment.name,
            "asset_type": investment.asset_type,
            "quantity": quantity,
            "average_price": average_price,
            "cost": cost,
            "current_price": current_price,
            "current_value": current_value,
            "gain": gain,
            "gain_pct": gain_pct,
            "currency": quote.get("currency", "") if quote else "",
        })

    investment_total_cost = round(investment_total_cost, 2)
    investment_market_value = round(investment_market_value, 2)
    investment_gain = round(investment_market_value - investment_total_cost, 2) if investments and priced_investments == len(investments) else None
    investment_return = round((investment_gain / investment_total_cost) * 100, 1) if investment_gain is not None and investment_total_cost else None

    # Voor de dashboardweergave: grootste posities eerst.
    investment_rows.sort(key=lambda item: (item["current_value"] if item["current_value"] is not None else item["cost"]), reverse=True)

    income_total = round(float(income_total), 2)
    expense_total = round(float(expense_total), 2)
    balance = round(income_total - expense_total, 2)
    savings_rate = round((balance / income_total) * 100, 1) if income_total else 0

    years = {date.today().year}
    years.update(y for (y,) in db.session.query(func.strftime("%Y", Expense.date)).filter(Expense.user_id == current_user.id).distinct().all() if y)
    years.update(y for (y,) in db.session.query(func.strftime("%Y", Income.start_date)).filter(Income.user_id == current_user.id).distinct().all() if y)
    years = sorted({int(y) for y in years} | {selected_year}, reverse=True)

    return render_template(
        "index.html", selected_year=selected_year, years=years,
        income_total=income_total, expense_total=expense_total,
        balance=balance, savings_rate=savings_rate,
        month_names=month_names, income_values=income_values,
        expense_values=expense_values,
        category_labels=[c for c, _ in category_rows],
        category_values=[round(float(v or 0), 2) for _, v in category_rows],
        recent_expenses=recent_expenses, recent_incomes=recent_incomes,
        investment_rows=investment_rows,
        investment_total_cost=investment_total_cost,
        investment_market_value=investment_market_value,
        investment_gain=investment_gain,
        investment_return=investment_return,
        investment_count=len(investments),
        investment_priced_count=priced_investments
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

    q = owned_query(Expense)
    if start_date:
        q = q.filter(Expense.user_id == current_user.id, Expense.date >= start_date)
    if end_date:
        q = q.filter(Expense.user_id == current_user.id, Expense.date <= end_date)
    if selected_category:
        q = q.filter(Expense.user_id == current_user.id, Expense.category == selected_category)
    expenses = q.order_by(Expense.date.desc(), Expense.id.desc()).all()
    total = round(sum(e.amount for e in expenses), 2)

    cat_q = db.session.query(Expense.category, func.sum(Expense.amount)).filter(Expense.user_id == current_user.id)
    day_q = db.session.query(Expense.date, func.sum(Expense.amount)).filter(Expense.user_id == current_user.id)
    cat_rows = cat_q.filter(*([Expense.user_id == current_user.id, Expense.date >= start_date] if start_date else []),
                            *([Expense.user_id == current_user.id, Expense.date <= end_date] if end_date else []),
                            *([Expense.user_id == current_user.id, Expense.category == selected_category] if selected_category else [])).group_by(Expense.category).all()
    day_rows = day_q.filter(*([Expense.user_id == current_user.id, Expense.date >= start_date] if start_date else []),
                            *([Expense.user_id == current_user.id, Expense.date <= end_date] if end_date else []),
                            *([Expense.user_id == current_user.id, Expense.category == selected_category] if selected_category else [])).group_by(Expense.date).order_by(Expense.date).all()
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
        date=d,
        user_id=current_user.id
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

    expense = owned_or_404(Expense, expense_id)

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

    expense = owned_or_404(Expense, expense_id)

    return render_template(
        "edit.html",
        expense=expense,
        categories=CATEGORIES,
        today=date.today().isoformat()
    )


@app.route("/expenses/edit/<int:expense_id>", methods=["POST"])
@login_required
def edit_post(expense_id):

    expense = owned_or_404(Expense, expense_id)

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
    incomes = owned_query(Income).order_by(
        Income.start_date.desc(),
        Income.id.desc()
    ).all()

    total = round(sum(i.amount for i in incomes), 2)

    month_expression = func.strftime("%Y-%m", Income.start_date)
    month_rows = db.session.query(
        month_expression,
        func.sum(Income.amount)
    ).filter(Income.user_id == current_user.id).group_by(
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
        amount = convert_amount(amount, current_user.currency, "EUR")
        if amount is None:
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
        end_date=end_date,
        user_id=current_user.id
    )

    db.session.add(income_item)
    db.session.commit()

    flash("Income added.", "success")
    return redirect(url_for("income"))


@app.route("/income/delete/<int:income_id>", methods=["POST"])
@login_required
def delete_income(income_id):
    income_item = owned_or_404(Income, income_id)

    db.session.delete(income_item)
    db.session.commit()

    flash("Income deleted.", "success")
    return redirect(url_for("income"))


@app.route("/income/edit/<int:income_id>", methods=["GET"])
@login_required
def edit_income(income_id):
    income_item = owned_or_404(Income, income_id)

    return render_template(
        "income_edit.html",
        income=income_item,
        categories=INCOME_CATEGORIES
    )


@app.route("/income/edit/<int:income_id>", methods=["POST"])
@login_required
def edit_income_post(income_id):
    income_item = owned_or_404(Income, income_id)

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


def investment_search(query):
    """Search Yahoo Finance symbols for the investment autocomplete."""
    clean = " ".join((query or "").split())[:80]
    if len(clean) < 2:
        return []

    encoded = urllib.parse.quote(clean)
    data = fetch_url(
        f"https://query1.finance.yahoo.com/v1/finance/search?q={encoded}&quotesCount=12&newsCount=0"
    )
    if not data:
        return []

    try:
        payload = json.loads(data)
        results = []
        for item in payload.get("quotes", []):
            symbol = (item.get("symbol") or "").strip().upper()
            name = (item.get("longname") or item.get("shortname") or symbol).strip()
            quote_type = (item.get("quoteType") or "").upper()
            exchange = (item.get("exchange") or item.get("fullExchangeName") or "").strip()
            if not symbol or not name:
                continue

            if quote_type == "EQUITY":
                asset_type = "Aandeel"
            elif quote_type in {"ETF", "MUTUALFUND"}:
                asset_type = "ETF"
            elif quote_type in {"CRYPTOCURRENCY", "CRYPTO"}:
                asset_type = "Crypto"
            elif quote_type == "BOND":
                asset_type = "Obligatie"
            else:
                asset_type = "Andere"

            results.append({
                "symbol": symbol,
                "name": name,
                "asset_type": asset_type,
                "exchange": exchange,
            })
        return results[:10]
    except Exception:
        return []


@app.route("/api/investing/search")
@limiter.limit("30 per minute")
@login_required
def investment_search_api():
    query = (request.args.get("q") or "").strip()
    return {"results": investment_search(query)}


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


def _parse_news_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        pass
    try:
        from email.utils import parsedate_to_datetime
        parsed = parsedate_to_datetime(value)
        return parsed.replace(tzinfo=None) if parsed else None
    except Exception:
        return None


def _news_relevance(title, description=""):
    text = f"{title} {description}".lower()
    high_value = [
        "earnings", "resultaten", "kwartaal", "omzet", "winst", "verlies",
        "guidance", "outlook", "dividend", "overname", "fusie", "acquisitie",
        "ipo", "beursgang", "faillissement", "restructuring", "reorganisatie",
        "ceo", "cfo", "fed", "ecb", "interest", "rente", "inflatie", "cpi",
        "jobs report", "werkgelegenheid", "recessie", "tarief", "tarieven",
        "sanctie", "regulation", "regelgeving", "goedkeuring", "approval",
        "product launch", "productlancering", "forecast", "verwachting",
        "price target", "koersdoel", "upgrade", "downgrade", "guidance"
    ]
    low_value = [
        "beste aandelen", "top 10", "dit aandeel kan", "should you buy",
        "koop nu", "sell now", "stock picks", "horoscope", "quiz"
    ]
    score = sum(3 for word in high_value if word in text)
    score -= sum(4 for word in low_value if word in text)
    return score


def _google_news_items(query, selected_date=None):
    date_filter = ""
    if selected_date:
        next_day = selected_date + timedelta(days=1)
        date_filter = f" after:{selected_date.isoformat()} before:{next_day.isoformat()}"
    encoded = urllib.parse.quote((query + date_filter)[:450])
    data = fetch_url(
        f"https://news.google.com/rss/search?q={encoded}&hl=nl-BE&gl=BE&ceid=BE:nl",
        timeout=12
    )
    if not data:
        return []
    try:
        root = ET.fromstring(data)
        items = []
        for item in root.findall("./channel/item"):
            published_raw = item.findtext("pubDate") or ""
            published_dt = _parse_news_date(published_raw)
            if selected_date and (not published_dt or published_dt.date() != selected_date):
                continue
            source_node = item.find("source")
            source = (source_node.text or "").strip() if source_node is not None else ""
            title = (item.findtext("title") or "").strip()
            link = safe_external_url(item.findtext("link") or "")
            items.append({
                "title": title,
                "link": link,
                "published": published_dt.strftime("%d-%m-%Y %H:%M") if published_dt else published_raw,
                "published_iso": published_dt.isoformat() if published_dt else "",
                "source": source or "Google News",
                "relevance": _news_relevance(title)
            })
        return items
    except Exception:
        return []


def _yahoo_news_items(query):
    encoded = urllib.parse.quote(" ".join((query or "").split())[:120])
    data = fetch_url(
        f"https://query1.finance.yahoo.com/v1/finance/search?q={encoded}&quotesCount=0&newsCount=25",
        timeout=10
    )
    if not data:
        return []
    try:
        payload = json.loads(data)
        items = []
        for item in payload.get("news", []):
            title = (item.get("title") or "").strip()
            link = safe_external_url(item.get("link") or "")
            timestamp = item.get("providerPublishTime")
            published_dt = datetime.fromtimestamp(float(timestamp)) if timestamp else None
            if not title or not link:
                continue
            items.append({
                "title": title,
                "link": link,
                "published": published_dt.strftime("%d-%m-%Y %H:%M") if published_dt else "",
                "published_iso": published_dt.isoformat() if published_dt else "",
                "source": (item.get("publisher") or "Yahoo Finance").strip(),
                "relevance": _news_relevance(title, item.get("summary") or "")
            })
        return items
    except Exception:
        return []


def market_news(topic=None, selected_date=None):
    # Google News levert historische resultaten; Yahoo Finance vult die aan
    # met financieel nieuws. We gebruiken geen scraping van Google Finance.
    clean_topic = " ".join((topic or "").split())[:100]
    queries = [
        "aandelen OR aandelenmarkt OR beurs OR economie OR ETF OR crypto OR rente",
        "stock market OR earnings OR economy OR ETF OR crypto OR interest rates"
    ]
    if clean_topic:
        queries = [f"({q}) {clean_topic}" for q in queries]

    items = []
    for q in queries:
        items.extend(_google_news_items(q, selected_date))

    # Yahoo Finance is especially useful for finance-specific headlines.
    items.extend(_yahoo_news_items(clean_topic or "stock market finance"))

    # Bij een gekozen datum houden we alleen nieuws van die exacte datum over.
    if selected_date:
        items = [
            item for item in items
            if item.get("published_iso") and item["published_iso"][:10] == selected_date.isoformat()
        ]

    seen = set()
    unique = []
    for item in sorted(
        items,
        key=lambda x: (x.get("relevance", 0), x.get("published_iso", "")),
        reverse=True
    ):
        key = " ".join(item["title"].lower().split())
        if key in seen:
            continue
        seen.add(key)
        if item.get("relevance", 0) < -1:
            continue
        unique.append(item)

    # Toon uiteindelijk het nieuwste nieuws eerst; de score filtert vooral ruis.
    unique.sort(key=lambda x: x.get("published_iso", ""), reverse=True)
    return unique[:60]


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


def gemini_chat(prompt, model=None):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is niet ingesteld.")

    model = model or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "system_instruction": (
                "Je bent FINTRACK AI, een Nederlandstalige financiële "
                "onderzoeksassistent. Gebruik uitsluitend de aangeleverde actuele "
                "marktdata en nieuws als feitelijke actuele context. Verzin geen "
                "prijzen, rendementen, nieuwsfeiten of cijfers. Geef geen "
                "gegarandeerde rendementen en presenteer geen koop- of "
                "verkoopbeslissing als zekerheid. Maak duidelijk onderscheid "
                "tussen feiten, interpretatie, scenario's en onzekerheid. "
                "Bespreek relevante risico's en Belgische aandachtspunten. "
                "Als de aangeleverde informatie onvoldoende is, zeg dat expliciet. "
                "Antwoord helder in het Nederlands met korte kopjes en bullets "
                "waar dat de leesbaarheid verbetert."
            ),
            "temperature": 0.2,
            "max_output_tokens": 900,
        },
    )

    return (getattr(response, "text", None) or "").strip()


@app.route("/investing")
@login_required
def investing():
    holdings = owned_query(Investment).order_by(Investment.symbol).all()
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
                              quantity=quantity, average_price=average_price,
                              user_id=current_user.id))
    db.session.commit()
    flash("Belegging toegevoegd.", "success")
    return redirect(url_for("investing"))


@app.route("/investing/delete/<int:investment_id>", methods=["POST"])
@login_required
def delete_investment(investment_id):
    item = owned_or_404(Investment, investment_id)
    db.session.delete(item)
    db.session.commit()
    flash("Belegging verwijderd.", "success")
    return redirect(url_for("investing"))


@app.route("/market")
@login_required
def market():
    selected_date_raw = (request.args.get("date") or date.today().isoformat()).strip()
    selected_date = parse_date_or_none(selected_date_raw)
    if not selected_date:
        selected_date = date.today()
    topic = " ".join((request.args.get("q") or "").split())[:100]
    news = market_news(topic=topic, selected_date=selected_date)
    snapshot = market_snapshot()
    return render_template(
        "market.html",
        news=news,
        snapshot=snapshot,
        selected_date=selected_date.isoformat(),
        topic=topic
    )


@app.route("/ai-investor", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", methods=["POST"])
def ai_investor():
    answer = None
    question = ""

    if request.method == "POST":
        question = (request.form.get("question") or "").strip()

        if not question:
            flash("Stel eerst een vraag.", "error")
        else:
            holdings = owned_query(Investment).all()
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
                answer = gemini_chat(prompt)
                if not answer:
                    flash("De lokale AI gaf geen antwoord terug.", "error")
            except urllib.error.URLError:
                flash(
                    "De lokale AI is niet bereikbaar of reageert niet op tijd. Controleer of Ollama draait "
                    "en of het ingestelde model geïnstalleerd is.",
                    "error"
                )
            except Exception as exc:
                flash(f"AI-aanvraag mislukt: {exc}", "error")

    return render_template("ai_investor.html", answer=answer, question=question)



