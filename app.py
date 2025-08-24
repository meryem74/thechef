import os
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Restaurant, Menu, Order, OrderItem, Comment

# --------------------
# Flask Ayarları
# --------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///revstoran.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB resim limiti
app.config['SECRET_KEY'] = 'supersecretkey'  # üretimde çevre değişkeninden çekin
app.config['SESSION_PERMANENT'] = False

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# MODELS ile APP'i birbirine bağla
db.init_app(app)

# Upload klasörü yoksa oluştur
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --------------------
# Yardımcılar
# --------------------

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return User.query.get(uid)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Devam etmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login', next=request.path))
        return view_func(*args, **kwargs)
    return wrapper


def owner_required(restaurant: Restaurant):
    user = current_user()
    if not user or restaurant.owner_id != user.id:
        abort(403)


# --------------------
# Veritabanını oluştur
# --------------------
with app.app_context():
    db.create_all()


# --------------------
# Kullanıcı Yönetimi
# --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        raw_password = request.form.get('password', '')

        if not username or not email or not raw_password:
            flash('Tüm alanlar zorunludur.', 'danger')
            return redirect(url_for('register'))

        # Benzersiz email kontrolü
        if User.query.filter_by(email=email).first():
            flash('Bu email ile zaten bir hesap var.', 'danger')
            return redirect(url_for('register'))

        # Benzersiz kullanıcı adı opsiyonel ama ekleyelim
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı kullanımda.', 'danger')
            return redirect(url_for('register'))

        password = generate_password_hash(raw_password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Kayıt başarılı, giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Giriş başarılı', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('index'))
        flash('Hatalı giriş bilgileri', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Çıkış yapıldı', 'info')
    return redirect(url_for('index'))


# --------------------
# Anasayfa / Restoran Görüntüleme
# --------------------
@app.route('/')
def index():
    restaurants = Restaurant.query.order_by(Restaurant.id.desc()).all()
    return render_template('index.html', restaurants=restaurants, user=current_user())


@app.route('/restaurant/<int:id>')
def restaurant_detail(id):
    restaurant = Restaurant.query.get_or_404(id)
    menu_items = Menu.query.filter_by(restaurant_id=id).all()
    comments = Comment.query.filter_by(restaurant_id=id).order_by(Comment.id.desc()).all()
    return render_template(
        'restaurant_detail.html',
        restaurant=restaurant,
        menu_items=menu_items,
        comments=comments,
        user=current_user()
    )


# --------------------
# Restoran Yönetimi
# --------------------
@app.route('/add_restaurant', methods=['GET', 'POST'])
@login_required
def add_restaurant():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        address = request.form.get('address', '').strip()
        image = request.files.get('image')

        filename = None
        if image and image.filename:
            if not allowed_file(image.filename):
                flash('İzin verilen resim uzantıları: png, jpg, jpeg, gif, webp', 'danger')
                return redirect(url_for('add_restaurant'))
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_restaurant = Restaurant(
            owner_id=session['user_id'],
            name=name,
            description=description,
            address=address,
            image_path=f"uploads/{filename}" if filename else None
        )
        db.session.add(new_restaurant)
        db.session.commit()
        flash('Restoran eklendi.', 'success')
        return redirect(url_for('index'))

    return render_template('add_restaurant.html', user=current_user())


@app.route('/edit_restaurant/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_restaurant(id):
    restaurant = Restaurant.query.get_or_404(id)
    owner_required(restaurant)

    if request.method == 'POST':
        restaurant.name = request.form.get('name', restaurant.name).strip()
        restaurant.description = request.form.get('description', restaurant.description).strip()
        restaurant.address = request.form.get('address', restaurant.address).strip()

        image = request.files.get('image')
        if image and image.filename:
            if not allowed_file(image.filename):
                flash('İzin verilen resim uzantıları: png, jpg, jpeg, gif, webp', 'danger')
                return redirect(url_for('edit_restaurant', id=id))
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            restaurant.image_path = f"uploads/{filename}"

        db.session.commit()
        flash('Restoran güncellendi.', 'success')
        return redirect(url_for('restaurant_detail', id=id))

    return render_template('edit_restaurant.html', restaurant=restaurant, user=current_user())


@app.route('/delete_restaurant/<int:id>', methods=['POST'])
@login_required
def delete_restaurant(id):
    restaurant = Restaurant.query.get_or_404(id)
    owner_required(restaurant)

    db.session.delete(restaurant)
    db.session.commit()
    flash('Restoran silindi.', 'info')
    return redirect(url_for('index'))


# --------------------
# Menü Yönetimi
# --------------------
@app.route('/add_menu_item/<int:restaurant_id>', methods=['GET', 'POST'])
@login_required
def add_menu_item(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    owner_required(restaurant)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price_str = request.form.get('price', '0').replace(',', '.')
        try:
            price = float(price_str)
        except ValueError:
            flash('Geçersiz fiyat.', 'danger')
            return redirect(url_for('add_menu_item', restaurant_id=restaurant_id))

        image = request.files.get('image')
        filename = None
        if image and image.filename:
            if not allowed_file(image.filename):
                flash('İzin verilen resim uzantıları: png, jpg, jpeg, gif, webp', 'danger')
                return redirect(url_for('add_menu_item', restaurant_id=restaurant_id))
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_item = Menu(
            restaurant_id=restaurant_id,
            name=name,
            description=description,
            price=price,
            image_path=f"uploads/{filename}" if filename else None
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Menü ürünü eklendi.', 'success')
        return redirect(url_for('restaurant_detail', id=restaurant_id))

    return render_template('add_menu_item.html', restaurant_id=restaurant_id, user=current_user())


@app.route('/edit_menu_item/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_menu_item(id):
    item = Menu.query.get_or_404(id)
    restaurant = Restaurant.query.get_or_404(item.restaurant_id)
    owner_required(restaurant)

    if request.method == 'POST':
        item.name = request.form.get('name', item.name).strip()
        item.description = request.form.get('description', item.description).strip()
        price_str = request.form.get('price', str(item.price)).replace(',', '.')
        try:
            item.price = float(price_str)
        except ValueError:
            flash('Geçersiz fiyat.', 'danger')
            return redirect(url_for('edit_menu_item', id=id))

        image = request.files.get('image')
        if image and image.filename:
            if not allowed_file(image.filename):
                flash('İzin verilen resim uzantıları: png, jpg, jpeg, gif, webp', 'danger')
                return redirect(url_for('edit_menu_item', id=id))
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            item.image_path = f"uploads/{filename}"

        db.session.commit()
        flash('Menü ürünü güncellendi.', 'success')
        return redirect(url_for('restaurant_detail', id=item.restaurant_id))

    return render_template('edit_menu_item.html', item=item, user=current_user())


@app.route('/delete_menu_item/<int:id>', methods=['POST'])
@login_required
def delete_menu_item(id):
    item = Menu.query.get_or_404(id)
    restaurant = Restaurant.query.get_or_404(item.restaurant_id)
    owner_required(restaurant)

    db.session.delete(item)
    db.session.commit()
    flash('Menü ürünü silindi.', 'info')
    return redirect(url_for('restaurant_detail', id=restaurant.id))


# --------------------
# Sepet / Sipariş
# --------------------

def _init_cart():
    if 'cart' not in session:
        session['cart'] = {"restaurant_id": None, "items": []}


def _cart_total():
    _init_cart()
    return sum(i['price'] * i['quantity'] for i in session['cart']['items'])


@app.route('/cart')
def cart():
    _init_cart()
    return render_template('cart.html', cart=session['cart'], total=_cart_total(), user=current_user())


@app.route('/add_to_cart/<int:menu_id>', methods=['POST'])
def add_to_cart(menu_id):
    _init_cart()
    menu_item = Menu.query.get_or_404(menu_id)
    item_restaurant_id = menu_item.restaurant_id

    # Tek restoran kuralı: farklı restoran ürünü eklenirse sepeti sıfırla (veya kullanıcıya sorabilirsiniz)
    if session['cart']['restaurant_id'] is None:
        session['cart']['restaurant_id'] = item_restaurant_id
    elif session['cart']['restaurant_id'] != item_restaurant_id:
        session['cart'] = {"restaurant_id": item_restaurant_id, "items": []}
        flash('Sepet farklı bir restoran için sıfırlandı.', 'info')

    # Aynı üründen varsa miktarı artır
    for it in session['cart']['items']:
        if it['id'] == menu_item.id:
            it['quantity'] += 1
            session.modified = True
            return redirect(url_for('cart'))

    session['cart']['items'].append({
        "id": menu_item.id,
        "name": menu_item.name,
        "price": float(menu_item.price),
        "quantity": 1
    })
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/update_cart_quantity/<int:menu_id>', methods=['POST'])
def update_cart_quantity(menu_id):
    _init_cart()
    try:
        qty = int(request.form.get('quantity', '1'))
    except ValueError:
        qty = 1
    qty = max(1, min(50, qty))

    for it in session['cart']['items']:
        if it['id'] == menu_id:
            it['quantity'] = qty
            session.modified = True
            break
    return redirect(url_for('cart'))


@app.route('/remove_from_cart/<int:menu_id>', methods=['POST'])
def remove_from_cart(menu_id):
    _init_cart()
    session['cart']['items'] = [i for i in session['cart']['items'] if i['id'] != menu_id]
    if not session['cart']['items']:
        session['cart']['restaurant_id'] = None
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    session['cart'] = {"restaurant_id": None, "items": []}
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    _init_cart()
    items = session['cart']['items']
    if not items:
        flash('Sepetiniz boş.', 'warning')
        return redirect(url_for('cart'))

    restaurant_id = session['cart']['restaurant_id']
    total_price = _cart_total()

    new_order = Order(
        customer_id=session['user_id'],
        restaurant_id=restaurant_id,
        total_price=total_price,
        status='pending'
    )
    db.session.add(new_order)
    db.session.commit()

    for it in items:
        db.session.add(OrderItem(
            order_id=new_order.id,
            menu_id=it['id'],
            quantity=it['quantity'],
            price=it['price']
        ))

    db.session.commit()
    session['cart'] = {"restaurant_id": None, "items": []}
    flash('Siparişiniz alındı!', 'success')
    return redirect(url_for('index'))


# --------------------
# Yorum Yönetimi
# --------------------
@app.route('/add_review/<int:restaurant_id>', methods=['POST'])
@login_required
def add_review(restaurant_id):
    content = (request.form.get('content') or '').strip()
    try:
        rating = int(request.form.get('rating', '5'))
    except ValueError:
        rating = 5
    rating = max(1, min(5, rating))

    if not content:
        flash('Yorum alanı boş olamaz.', 'danger')
        return redirect(url_for('restaurant_detail', id=restaurant_id))

    new_comment = Comment(
        user_id=session['user_id'],
        restaurant_id=restaurant_id,
        content=content,
        rating=rating
    )
    db.session.add(new_comment)
    db.session.commit()
    flash('Yorumunuz eklendi.', 'success')
    return redirect(url_for('restaurant_detail', id=restaurant_id))


@app.route('/reviews/<int:restaurant_id>')
def reviews(restaurant_id):
    comments = Comment.query.filter_by(restaurant_id=restaurant_id).order_by(Comment.id.desc()).all()
    return render_template('reviews.html', comments=comments, user=current_user())


# --------------------
# Hata Sayfaları (opsiyonel)
# --------------------
@app.errorhandler(403)
def forbidden(_e):
    return render_template('errors/403.html'), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template('errors/404.html'), 404



# --------------------
# CS50 için Çalıştır
# --------------------
if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=True
    )  
