from datetime import date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .database import db


class User(UserMixin, db.Model):
    """User account and personal preferences."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    display_name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(254), nullable=True)
    currency = db.Column(db.String(3), nullable=False, default="EUR", server_default="EUR")
    sector = db.Column(db.String(60), nullable=True)
    region = db.Column(db.String(40), nullable=True)
    avatar_color = db.Column(db.String(20), nullable=False, default="blue", server_default="blue")
    risk_profile = db.Column(db.String(20), nullable=False, default="balanced", server_default="balanced")
    investment_horizon = db.Column(db.String(20), nullable=False, default="medium", server_default="medium")
    monthly_investment_budget = db.Column(db.Float, nullable=False, default=0, server_default="0")
    emergency_fund_target = db.Column(db.Float, nullable=False, default=0, server_default="0")
    expenses = db.relationship("Expense", backref="user", lazy=True, cascade="all, delete-orphan")
    incomes = db.relationship("Income", backref="user", lazy=True, cascade="all, delete-orphan")
    investments = db.relationship("Investment", backref="user", lazy=True, cascade="all, delete-orphan")

    # Store only a password hash; the original password is never saved.
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Expense(db.Model):
    """Single expense belonging to one user."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)


class Income(db.Model):
    """Income record belonging to one user."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)


class Investment(db.Model):
    """Investment position belonging to one user."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    asset_type = db.Column(db.String(30), nullable=False, default="ETF")
    quantity = db.Column(db.Float, nullable=False, default=0)
    average_price = db.Column(db.Float, nullable=False, default=0)
    currency = db.Column(db.String(3), nullable=False, default="EUR", server_default="EUR")
    sector = db.Column(db.String(60), nullable=True)
    region = db.Column(db.String(40), nullable=True)


class SavingsGoal(db.Model):
    """Savings goal belonging to one user."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False, default=0)
    current_amount = db.Column(db.Float, nullable=False, default=0)
    deadline = db.Column(db.Date, nullable=True)
    color = db.Column(db.String(20), nullable=False, default="blue", server_default="blue")


class InvestmentEvent(db.Model):
    """Manual investment activity and dividend ledger."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    event_type = db.Column(db.String(20), nullable=False, default="buy")
    quantity = db.Column(db.Float, nullable=False, default=0)
    price = db.Column(db.Float, nullable=False, default=0)
    amount = db.Column(db.Float, nullable=False, default=0)
    currency = db.Column(db.String(3), nullable=False, default="EUR", server_default="EUR")
    date = db.Column(db.Date, nullable=False, default=date.today)
    note = db.Column(db.String(160), nullable=True)
