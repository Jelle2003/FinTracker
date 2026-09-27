from datetime import date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .database import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    display_name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(254), nullable=True)
    currency = db.Column(db.String(3), nullable=False, default="EUR", server_default="EUR")
    avatar_color = db.Column(db.String(20), nullable=False, default="blue", server_default="blue")
    expenses = db.relationship("Expense", backref="user", lazy=True, cascade="all, delete-orphan")
    incomes = db.relationship("Income", backref="user", lazy=True, cascade="all, delete-orphan")
    investments = db.relationship("Investment", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)


class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)


class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    asset_type = db.Column(db.String(30), nullable=False, default="ETF")
    quantity = db.Column(db.Float, nullable=False, default=0)
    average_price = db.Column(db.Float, nullable=False, default=0)
