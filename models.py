from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Kullanıcı tablosu
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # hashed password
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    restaurants = db.relationship('Restaurant', backref='owner', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    orders = db.relationship('Order', backref='customer', lazy=True)

# Restoran tablosu
class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(200), nullable=True)
    image_path = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    menus = db.relationship('Menu', backref='restaurant', lazy=True)
    comments = db.relationship('Comment', backref='restaurant', lazy=True)
    orders = db.relationship('Order', backref='restaurant', lazy=True)

# Menü tablosu
class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(200), nullable=True)

    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)

# Sipariş tablosu
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', lazy=True)

# Sipariş-Ürün ilişkisi
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)  # o anki fiyat

# Yorum tablosu
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)  # 1-5 arası puan
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
