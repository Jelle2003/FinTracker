from flask import Flask, render_template, request, url_for, flash, redirect, Response
from datetime import date, datetime, date as dt_date
from sqlalchemy import func
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from .database import db
from .models import User, Expense, Income


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

    start_str = (request.args.get("start") or "").strip()
    end_str = (request.args.get("end") or "").strip()
    selected_category = (request.args.get("category") or "").strip()

    start_date = parse_date_or_none(start_str)
    end_date = parse_date_or_none(end_str)

    if start_date and end_date and end_date < start_date:
        flash("End date cannot be before start date", "error")

        start_date = None
        end_date = None

        start_str = ""
        end_str = ""

    q = Expense.query

    if start_date:
        q = q.filter(Expense.date >= start_date)

    if end_date:
        q = q.filter(Expense.date <= end_date)

    if selected_category:
        q = q.filter(Expense.category == selected_category)

    expenses = q.order_by(
        Expense.date.desc(),
        Expense.id.desc()
    ).all()

    total = round(
        sum(e.amount for e in expenses),
        2
    )

    # ========================================================
    # PIE CHART
    # ========================================================

    cat_q = db.session.query(
        Expense.category,
        func.sum(Expense.amount)
    )

    if start_date:
        cat_q = cat_q.filter(Expense.date >= start_date)

    if end_date:
        cat_q = cat_q.filter(Expense.date <= end_date)

    if selected_category:
        cat_q = cat_q.filter(
            Expense.category == selected_category
        )

    cat_rows = cat_q.group_by(
        Expense.category
    ).all()

    cat_labels = [
        category
        for category, _ in cat_rows
    ]

    cat_values = [
        round(float(amount or 0), 2)
        for _, amount in cat_rows
    ]

    # ========================================================
    # DAY CHART
    # ========================================================

    day_q = db.session.query(
        Expense.date,
        func.sum(Expense.amount)
    )

    if start_date:
        day_q = day_q.filter(Expense.date >= start_date)

    if end_date:
        day_q = day_q.filter(Expense.date <= end_date)

    if selected_category:
        day_q = day_q.filter(
            Expense.category == selected_category
        )

    day_rows = day_q.group_by(
        Expense.date
    ).order_by(
        Expense.date
    ).all()

    day_labels = [
        day.isoformat()
        for day, _ in day_rows
    ]

    day_values = [
        round(float(amount or 0), 2)
        for _, amount in day_rows
    ]

    return render_template(
        "index.html",
        categories=CATEGORIES,
        today=date.today().isoformat(),
        expenses=expenses,
        total=total,
        start_str=start_str,
        end_str=end_str,
        selected_category=selected_category,
        cat_labels=cat_labels,
        cat_values=cat_values,
        day_labels=day_labels,
        day_values=day_values
    )


# ============================================================
# ADD EXPENSE
# ============================================================

@app.route("/add", methods=["POST"])
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

@app.route("/delete/<int:expense_id>", methods=["POST"])
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

@app.route("/edit/<int:expense_id>", methods=["GET"])
@login_required
def edit(expense_id):

    expense = Expense.query.get_or_404(expense_id)

    return render_template(
        "edit.html",
        expense=expense,
        categories=CATEGORIES,
        today=dt_date.today().isoformat()
    )


@app.route("/edit/<int:expense_id>", methods=["POST"])
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
# EXPORT CSV
# ============================================================

@app.route("/export.csv")
@login_required
def export_csv():

    start_str = (
        request.args.get("start") or ""
    ).strip()

    end_str = (
        request.args.get("end") or ""
    ).strip()

    selected_category = (
        request.args.get("category") or ""
    ).strip()

    start_date = parse_date_or_none(start_str)
    end_date = parse_date_or_none(end_str)

    q = Expense.query

    if start_date:
        q = q.filter(Expense.date >= start_date)

    if end_date:
        q = q.filter(Expense.date <= end_date)

    if selected_category:
        q = q.filter(
            Expense.category == selected_category
        )

    expenses = q.order_by(
        Expense.date,
        Expense.id
    ).all()

    lines = [
        "date; description; category; amount"
    ]

    for expense in expenses:
        lines.append(
            f"{expense.date.isoformat()}; "
            f"{expense.description}; "
            f"{expense.category}; "
            f"{expense.amount:.2f}"
        )

    csv_data = "\n".join(lines)

    fname_start = start_str or "all"
    fname_end = end_str or "all"

    filename = (
        f"expenses_{fname_start}_to_{fname_end}.csv"
    )

    return Response(
        csv_data,
        headers={
            "Content-Type": "text/csv",
            "Content-Disposition":
                f"attachment; filename={filename}"
        }
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        port=4848
    )
