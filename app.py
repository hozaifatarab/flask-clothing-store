"""
متجر ملابس اون لاين - لوحة تحكم ادمن + شات بوت كارم
Online Clothing Store with Admin Panel & Chatbot
"""
from flask import Flask, render_template, request, jsonify, session, g, redirect, url_for, send_from_directory, flash
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import os
from functools import wraps
from werkzeug.utils import secure_filename
from products import products as products_list
from dotenv import load_dotenv

# ==================== تحميل المتغيرات البيئية ====================
load_dotenv()

# ==================== الإعدادات ====================
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
DATABASE_URL = os.environ.get('DATABASE_URL', '')
DATABASE = 'products.db'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
CORS(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static/images', exist_ok=True)

# ==================== تحميل الردود ====================
def load_responses():
    responses_path = os.path.join(os.path.dirname(__file__), 'responses.json')
    if os.path.exists(responses_path):
        with open(responses_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

RESPONSES_DATA = load_responses()

# ==================== قاعدة البيانات ====================
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        category TEXT NOT NULL,
        stock INTEGER DEFAULT 0,
        available INTEGER DEFAULT 1,
        image TEXT,
        size TEXT DEFAULT '',
        color TEXT DEFAULT '',
        created_at TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        customer_phone TEXT,
        customer_address TEXT,
        total_price REAL,
        status TEXT DEFAULT 'pending',
        items TEXT,
        created_at TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        sender TEXT,
        message TEXT,
        timestamp TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin_credentials (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        username TEXT NOT NULL DEFAULT 'admin',
        password TEXT NOT NULL DEFAULT 'admin123'
    )''')
    
    cursor.execute('SELECT COUNT(*) as count FROM admin_credentials')
    admin_count = cursor.fetchone()['count']
    if admin_count == 0:
        cursor.execute('INSERT INTO admin_credentials (id, username, password) VALUES (1, ?, ?)', ('admin', 'admin123'))
    
    cursor.execute('SELECT COUNT(*) as count FROM products')
    product_count = cursor.fetchone()['count']
    
    if product_count == 0:
        for p in products_list:
            cursor.execute('''INSERT INTO products (name, description, price, category, image, created_at)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (p['name'], p.get('description', ''), p['price'], p['category'], p['image'], datetime.now().isoformat()))
        conn.commit()
        print(f"[OK] Database initialized with {len(products_list)} products")
    else:
        print(f"[OK] Database already has {product_count} products")
    
    conn.close()

with app.app_context():
    init_db()

# ==================== دوال مساعدة ====================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_admin_password_from_db():
    """جلب كلمة السر من قاعدة البيانات"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM admin_credentials WHERE id = 1')
    row = cursor.fetchone()
    conn.close()
    return row['password'] if row else None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') != True:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== التحكم في تسجيل الدخول ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        entered_password = request.form.get('password', '')
        env_password = os.environ.get('ADMIN_PASSWORD')
        db_password = get_admin_password_from_db()
        
        if entered_password == env_password or entered_password == db_password:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('كلمة السر غلط')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

@app.context_processor
def inject_user():
    return dict(is_admin=session.get('logged_in', False))

# ==================== خدمة الملفات المرفوعة ====================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==================== الصفحات الرئيسية ====================
@app.route('/')
def home():
    return redirect(url_for('index'))

@app.route('/index')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products ORDER BY id')
    products = cursor.fetchall()
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    if not product:
        return jsonify({'error': 'المنتج غير موجود'}), 404
    return render_template('product_detail.html', product=product)

@app.route('/mens')
def mens():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE category = 'mens' ORDER BY id")
    products = cursor.fetchall()
    return render_template('index.html', products=products)

@app.route('/womens')
def womens():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE category = 'womens' ORDER BY id")
    products = cursor.fetchall()
    return render_template('index.html', products=products)

@app.route('/cart')
def cart():
    return render_template('cart.html')

# ==================== API المنتجات ====================
@app.route('/api/products')
def api_get_products():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    if category == 'all':
        if search:
            cursor.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ?',
                (f'%{search}%', f'%{search}%'))
        else:
            cursor.execute('SELECT * FROM products ORDER BY id')
    else:
        if search:
            cursor.execute('SELECT * FROM products WHERE category = ? AND (name LIKE ? OR description LIKE ?)',
                (category, f'%{search}%', f'%{search}%'))
        else:
            cursor.execute('SELECT * FROM products WHERE category = ? ORDER BY id', (category,))
    
    products = cursor.fetchall()
    return jsonify([dict(p) for p in products])

@app.route('/api/product/<int:product_id>')
def api_get_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    if not product:
        return jsonify({'error': 'المنتج غير موجود'}), 404
    return jsonify(dict(product))

# ==================== API الشات ====================
@app.route('/api/messages', methods=['GET', 'POST'])
def api_messages():
    if request.method == 'GET':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM messages ORDER BY timestamp ASC LIMIT 100')
        messages = cursor.fetchall()
        return jsonify([dict(m) for m in messages])
    
    elif request.method == 'POST':
        data = request.get_json()
        sender = data.get('sender', 'زائر').strip()
        message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not sender or not message:
            return jsonify({'error': 'يرجى ملء جميع الحقول'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO messages (session_id, sender, message, timestamp) VALUES (?, ?, ?, ?)',
            (session_id, sender, message, datetime.now().isoformat()))
        conn.commit()
        msg_id = cursor.lastrowid
        cursor.execute('SELECT * FROM messages WHERE id = ?', (msg_id,))
        new_msg = cursor.fetchone()
        return jsonify(dict(new_msg))

@app.route('/api/messages', methods=['DELETE'])
def api_delete_messages():
    """مسح جميع رسائل الشات مع الاحتفاظ ببيانات الطلبات"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages')
    conn.commit()
    return jsonify({'success': True, 'message': 'تم مسح المحادثة بنجاح'})

@app.route('/api/messages/admin', methods=['POST'])
def api_admin_message():
    data = request.get_json()
    message = data.get('message', '').strip()
    session_id = data.get('session_id', 'default')
    
    if not message:
        return jsonify({'error': 'الرسالة فارغة'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (session_id, sender, message, timestamp) VALUES (?, ?, ?, ?)',
        (session_id, 'كارم', message, datetime.now().isoformat()))
    conn.commit()
    msg_id = cursor.lastrowid
    cursor.execute('SELECT * FROM messages WHERE id = ?', (msg_id,))
    new_msg = cursor.fetchone()
    return jsonify(dict(new_msg))

# ==================== API الطلبات ====================
@app.route('/api/orders', methods=['POST'])
def api_create_order():
    data = request.get_json()
    customer_name = data.get('customer_name', '').strip()
    customer_phone = data.get('customer_phone', '').strip()
    customer_address = data.get('customer_address', data.get('customer_email', '')).strip()
    items = data.get('items', [])
    total_price = data.get('total_price', 0)
    
    if not customer_name or not customer_phone or not items:
        return jsonify({'error': 'يرجى ملء جميع البيانات'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, status, items, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (customer_name, customer_phone, customer_address, total_price, 'pending', json.dumps(items), datetime.now().isoformat()))
    order_id = cursor.lastrowid
    
    for item in items:
        product_id = item['id']
        quantity = item['quantity']
        cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (quantity, product_id))
    
    conn.commit()
    return jsonify({'success': True, 'order_id': order_id, 'message': f'تم استلام طلبك برقم {order_id}.'})

@app.route('/api/orders/<int:order_id>')
def api_get_order(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cursor.fetchone()
    if not order:
        return jsonify({'error': 'الطلب غير موجود'}), 404
    order_dict = dict(order)
    order_dict['items'] = json.loads(order['items'])
    return jsonify(order_dict)

# ==================== لوحة التحكم ====================
@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@app.route('/admin_settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    message = None
    message_type = None
    
    if request.method == 'POST':
        new_username = request.form.get('new_username', '').strip()
        old_password = request.form.get('old_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        
        if not new_username or not old_password or not new_password:
            message = 'يرجى ملء جميع الحقول'
            message_type = 'error'
        else:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM admin_credentials WHERE id = 1')
            admin = cursor.fetchone()
            
            if not admin:
                message = 'خطأ في النظام'
                message_type = 'error'
            elif admin['password'] != old_password:
                message = 'كلمة السر الحالية غير صحيحة'
                message_type = 'error'
            else:
                cursor.execute('UPDATE admin_credentials SET username = ?, password = ? WHERE id = 1',
                    (new_username, new_password))
                conn.commit()
                message = 'تم تحديث بيانات الدخول بنجاح'
                message_type = 'success'
    
    return render_template('admin_settings.html', message=message, message_type=message_type)

# ==================== API إدارة المنتجات (مع رفع الصور) ====================
@app.route('/api/admin/products', methods=['GET', 'POST'])
def api_admin_products():
    if request.method == 'GET':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products ORDER BY id')
        products = cursor.fetchall()
        return jsonify([dict(p) for p in products])
    
    elif request.method == 'POST':
        image = ''
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                name_parts = filename.rsplit('.', 1)
                filename = f"{name_parts[0]}_{int(datetime.now().timestamp())}.{name_parts[1]}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = f'/uploads/{filename}'
        
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        price = float(data.get('price', 0))
        category = data.get('category', 'رجالي')
        stock = int(data.get('stock', 0))
        available = 1 if stock > 0 else 0
        
        if not image:
            image = data.get('image', '')
        
        if not name or not price:
            return jsonify({'error': 'اسم المنتج والسعر مطلوبين'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO products (name, description, price, category, stock, available, image, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, description, price, category, stock, available, image, datetime.now().isoformat()))
        conn.commit()
        product_id = cursor.lastrowid
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        return jsonify(dict(product))

@app.route('/api/admin/products/<int:product_id>', methods=['PUT', 'DELETE'])
def api_admin_product(product_id):
    if request.method == 'PUT':
        image = ''
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                name_parts = filename.rsplit('.', 1)
                filename = f"{name_parts[0]}_{int(datetime.now().timestamp())}.{name_parts[1]}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = f'/uploads/{filename}'
        
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        price = float(data.get('price', 0))
        category = data.get('category', 'رجالي')
        stock = int(data.get('stock', 0))
        available = 1 if stock > 0 else 0
        
        if not image:
            image = data.get('image', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        if image:
            cursor.execute('''UPDATE products SET name=?, description=?, price=?, category=?, stock=?, available=?, image=? WHERE id=?''',
                (name, description, price, category, stock, available, image, product_id))
        else:
            cursor.execute('''UPDATE products SET name=?, description=?, price=?, category=?, stock=?, available=? WHERE id=?''',
                (name, description, price, category, stock, available, product_id))
        
        conn.commit()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        return jsonify(dict(product))
    
    elif request.method == 'DELETE':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'تم حذف المنتج بنجاح'})

# ==================== API إدارة الطلبات ====================
@app.route('/api/admin/orders')
def api_admin_get_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
    orders = cursor.fetchall()
    orders_list = []
    for order in orders:
        order_dict = dict(order)
        order_dict['items'] = json.loads(order['items'])
        orders_list.append(order_dict)
    return jsonify(orders_list)

@app.route('/api/admin/orders/<int:order_id>/status', methods=['PUT'])
def api_update_order_status(order_id):
    data = request.get_json()
    status = data.get('status')
    if status not in ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']:
        return jsonify({'error': 'حالة غير صحيحة'}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    return jsonify({'success': True, 'message': f'تم تحديث الحالة'})

# ==================== الشات الذكي - كارم (نسخة سوداني) ====================
def find_response_in_json(user_message, responses_data):
    if not responses_data:
        return None
    user_lower = user_message.lower()
    for key, data in responses_data.items():
        if key == 'default':
            continue
        keywords = data.get('keywords', [])
        for keyword in keywords:
            if keyword in user_lower:
                return data.get('response', '')
    return None

def search_product_in_db(user_message):
    conn = get_db()
    cursor = conn.cursor()
    
    remove_words = ['عاوز', 'عايز', 'دلني', 'وريني', 'شوف', 'ارني', 'اقترح', 'نصح', 'عندك', 'في', 'متوفر', 'ال', 'هو', 'دا', 'ده', 'دي', 'بكم', 'كام', 'كم']
    search_query = user_message
    for word in remove_words:
        search_query = search_query.replace(word, '')
    search_query = search_query.strip()
    
    if len(search_query) < 2:
        return None
    
    keywords = {
        'قميص': 'قميص', 'كتان': 'كتان', 'رمادي': 'رمادي', 'بولو': 'بولو', 'اسود': 'اسود',
        'جينز': 'جينز', 'ازرق': 'ازرق', 'رسمي': 'رسمي', 'ابيض': 'ابيض',
        'حذاء': 'حذاء', 'بني': 'بني', 'رياضي': 'رياضي', 'sneakers': 'رياضي',
        'فستان': 'فستان', 'احمر': 'احمر', 'زفاف': 'زفاف', 'سهرة': 'سهرة',
        'صيفي': 'صيفي', 'مشجر': 'مشجر', 'عمل': 'عمل', 'اوفيس': 'عمل',
        'بوت': 'بوت', 'صندل': 'صندل', 'كعب': 'كعب', 'عالي': 'عالي',
        'رجالي': 'رجالي', 'نسائي': 'نسائي', 'شبابي': 'رجالي', 'بنات': 'نسائي',
        'دريس': 'فستان', 'شوز': 'حذاء', 'boots': 'بوت', 'sandals': 'صندل',
        'heels': 'كعب', 'dress': 'فستان', 'shirt': 'قميص',
    }
    
    search_terms = []
    for word in search_query.split():
        if word in keywords:
            search_terms.append(keywords[word])
        else:
            search_terms.append(word)
    
    search_text = ' '.join(search_terms)
    
    try:
        cursor.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ? LIMIT 5',
            (f'%{search_text}%', f'%{search_text}%'))
        products = cursor.fetchall()
        
        if not products:
            for term in search_terms:
                if len(term) > 1:
                    cursor.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ? LIMIT 3',
                        (f'%{term}%', f'%{term}%'))
                    products = cursor.fetchall()
                    if products:
                        break
        
        if not products:
            cursor.execute('SELECT * FROM products')
            all_products = cursor.fetchall()
            for p in all_products:
                desc = p['description'] or ''
                name = p['name'] or ''
                for word in search_query.split():
                    if len(word) > 1 and (word in desc or word in name):
                        products = [p]
                        break
                if products:
                    break
        
        if products:
            return [dict(p) for p in products]
    except Exception:
        return None
    
    return None

def get_products_by_category(category_name):
    """جلب منتجات حسب التصنيف"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE category = ? AND stock > 0', (category_name,))
    products = cursor.fetchall()
    return [dict(p) for p in products] if products else None

def build_product_card_html(product):
    """بناء HTML كارت المنتج"""
    image_url = product.get('image', '')
    name = product.get('name', '')
    price = product.get('price', 0)
    stock = product.get('stock', 0)
    desc = product.get('description', '')
    
    html = f'''
    <div style="display:flex;align-items:flex-start;background:white;border-radius:12px;padding:12px;box-shadow:0 2px 8px rgba(0,0,0,0.1);gap:12px;margin-top:8px;direction:rtl;">
        <img src="{image_url}" alt="{name}" style="width:80px;height:80px;object-fit:cover;border-radius:10px;flex-shrink:0;" onerror="this.src='https://via.placeholder.com/80?text=?'">
        <div style="flex:1;">
            <div style="font-weight:bold;font-size:14px;margin-bottom:4px;">{name}</div>
            <div style="color:#D32F2F;font-weight:bold;font-size:15px;margin-bottom:4px;">{price} ريال</div>
            <div style="font-size:11px;color:#666;line-height:1.4;">{desc}</div>
            <div style="font-size:11px;margin-top:4px;">{"✅ متوفر" if stock > 0 else "❌ غير متوفر"}</div>
        </div>
    </div>'''
    return html

def generate_smart_response(user_message):
    """توليد رد كارم الذكي"""
    user_message_lower = user_message.lower()
    
    # ====== 1. التحية ======
    if any(word in user_message_lower for word in ['سلام', 'السلام عليكم', 'مرحبا', 'اهلا', 'hi', 'hello']):
        reply = "وعليكم السلام ورحمة الله 👋\n"
        reply += "مرحبا بيك في متجرنا 🛍️\n"
        reply += "معاك كارم 😊\n\n"
        reply += "عندنا تشكيلة حلوة:\n"
        reply += "👔 رجالي: قمصان، بولو، جينز، احذية\n"
        reply += "👗 نسائي: فساتين، صنادل، بوت، كعب\n\n"
        reply += "قولي عاوز تشوف شنو بالضبط؟\n"
        reply += "تحب اطلبو ليك؟ او عندك سؤال تاني؟"
        return json.dumps({'reply': reply, 'products': [], 'html_cards': ''})
    
    # ====== 2. البحث في responses.json ======
    response_from_json = find_response_in_json(user_message, RESPONSES_DATA)
    if response_from_json:
        return json.dumps({'reply': response_from_json, 'products': [], 'html_cards': ''})
    
    # ====== 3. كلمات مفتاحية خاصة ======
    if any(word in user_message_lower for word in ['شنط', 'شنتة', 'حقيبة', 'حقائب']):
        reply = "حاليا عندنا ملابس واحذية بس 😅\n\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
        return json.dumps({'reply': reply, 'products': [], 'html_cards': ''})
    
    if 'التوصيل بكم' in user_message_lower or 'بكام التوصيل' in user_message_lower:
        reply = "داخل المدينة 25 ريال 🚚\n\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
        return json.dumps({'reply': reply, 'products': [], 'html_cards': ''})
    
    if 'الفرق' in user_message_lower and ('بوت' in user_message_lower or 'صندل' in user_message_lower):
        reply = "خليني اوضح ليك الفرق 😊\n\n"
        # جلب البوت والصندل
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE (name LIKE '%بوت%' OR name LIKE '%صندل%') AND stock > 0")
        products = cursor.fetchall()
        
        cards = ''
        for p in products:
            p_dict = dict(p)
            cards += build_product_card_html(p_dict)
            
        reply += "البوت شتوي وجلد ومناسب للشتاء ❄️\n"
        reply += "الصندل صيفي ومريح ومناسب للصيف ☀️\n\n"
        reply += "تحب اطلبو ليك؟ او عندك سؤال تاني؟"
        return json.dumps({'reply': reply, 'products': [dict(p) for p in products], 'html_cards': cards})
    
    # ====== 4. عرض منتجات حسب الفئة ======
    if any(word in user_message_lower for word in ['فساتين', 'فستان', 'دريس']):
        products = get_products_by_category('نسائي')
        if products:
            reply = "الفساتين المتوفرة عندنا 👗:\n\n"
            cards = ''
            for p in products:
                cards += build_product_card_html(p)
                reply += f"- {p['name']}: {p['price']} ريال\n"
            reply += "\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
            return json.dumps({'reply': reply, 'products': products, 'html_cards': cards})
    
    if any(word in user_message_lower for word in ['رجالي', 'رجال', 'شبابي']):
        products = get_products_by_category('رجالي')
        if products:
            reply = "الملابس الرجالية المتوفرة 👔:\n\n"
            cards = ''
            for p in products:
                cards += build_product_card_html(p)
                reply += f"- {p['name']}: {p['price']} ريال\n"
            reply += "\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
            return json.dumps({'reply': reply, 'products': products, 'html_cards': cards})
    
    if any(word in user_message_lower for word in ['نسائي', 'نساء', 'بنات', 'حريم']):
        products = get_products_by_category('نسائي')
        if products:
            reply = "الملابس النسائية المتوفرة 👗:\n\n"
            cards = ''
            for p in products:
                cards += build_product_card_html(p)
                reply += f"- {p['name']}: {p['price']} ريال\n"
            reply += "\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
            return json.dumps({'reply': reply, 'products': products, 'html_cards': cards})
    
    if any(word in user_message_lower for word in ['احذية', 'حذاء', 'شوز', 'boots', 'sneakers']):
        products = get_products_by_category('رجالي')  # Shoes are in رجالي category
        if not products:
            products = []
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE name LIKE '%حذاء%' OR name LIKE '%بوت%' OR name LIKE '%صندل%' OR name LIKE '%كعب%'")
        shoes = cursor.fetchall()
        for s in shoes:
            s_dict = dict(s)
            if s_dict not in products:
                products.append(s_dict)
        if products:
            reply = "الاحذية المتوفرة عندنا 👟:\n\n"
            cards = ''
            for p in products:
                cards += build_product_card_html(p)
                reply += f"- {p['name']}: {p['price']} ريال\n"
            reply += "\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
            return json.dumps({'reply': reply, 'products': products, 'html_cards': cards})
    
    # ====== 5. وريني / عايز اشوف ======
    if any(word in user_message_lower for word in ['وريني', 'عايز اشوف', 'ارني', 'شوف']):
        # استخراج اسم المنتج
        show_query = user_message_lower.replace('وريني', '').replace('عايز اشوف', '').replace('ارني', '').replace('شوف', '').strip()
        if show_query:
            products_found = search_product_in_db(show_query)
            if products_found:
                reply = "تفضلي 👇\n\n"
                cards = ''
                for p in products_found:
                    cards += build_product_card_html(p)
                    reply += f"- {p['name']}: {p['price']} ريال\n"
                reply += "\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
                return json.dumps({'reply': reply, 'products': products_found, 'html_cards': cards})
    
    if any(word in user_message_lower for word in ['عايزة فستان', 'عاوزة فستان', 'بدي فستان', 'ابي فستان']):
        if 'شغل' in user_message_lower or 'عمل' in user_message_lower or 'اوفيس' in user_message_lower:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE name LIKE '%عمل%' OR name LIKE '%اوفيس%' OR name LIKE '%رسمي%'")
            products = cursor.fetchall()
            if products:
                reply = "فستان العمل المثالي ليكي 👗\n\n"
                cards = ''
                for p in products:
                    p_dict = dict(p)
                    cards += build_product_card_html(p_dict)
                    reply += f"- {p_dict['name']}: {p_dict['price']} ريال\n"
                reply += "\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
                return json.dumps({'reply': reply, 'products': [dict(p) for p in products], 'html_cards': cards})
    
    # ====== 6. استفسار عن الكمية ======
    if any(word in user_message_lower for word in ['متبقي', 'كم تبقى', 'الكمية', 'موجود', 'منها']):
        search_result = search_product_in_db(user_message)
        if search_result:
            p = search_result[0]
            reply = f"{p['name']}:\n"
            reply += f"المتبقي في المخزون: {p['stock']} قطعة ✅\n\n"
            reply += "تحب اطلبو ليك؟ او عندك سؤال تاني؟"
            return json.dumps({'reply': reply, 'products': [p], 'html_cards': build_product_card_html(p)})
    
    # ====== 7. عايز اطلب ======
    if any(word in user_message_lower for word in ['عايز اطلب', 'عاوز اطلب', 'اطلب', 'احجز', 'طلب']):
        reply = "تمام 👍\n\n"
        reply += "ابعتلي رقمك وعنوانك عشان نكمل الطلب.\n"
        reply += "ونحن نتواصل معاك قريب.\n\n"
        reply += "تحب اطلبو ليك؟ او عندك سؤال تاني؟"
        return json.dumps({'reply': reply, 'products': [], 'html_cards': ''})
    
    # ====== 8. البحث عن منتج ======
    product_result = search_product_in_db(user_message)
    
    if product_result:
        product = product_result[0]
        stock = product.get('stock', 0)
        
        if stock <= 0:
            reply = "المنتج دا حاليا غير متوفر 😅\n"
            reply += "احجزو ليك اول ما يتوفر؟\n\n"
            reply += "تحب اطلبو ليك؟ او عندك سؤال تاني؟"
            return json.dumps({'reply': reply, 'products': [product], 'html_cards': build_product_card_html(product)})
        
        reply = f"متوفر عندنا ✅\n\n"
        reply += f"الاسم: {product['name']}\n"
        reply += f"السعر: {product['price']} ريال\n"
        reply += f"الوصف: {product.get('description', '')}\n"
        reply += f"الكمية المتوفرة: {product['stock']} قطعة\n\n"
        reply += f"طرق الدفع:\n"
        reply += "✅ كاش عند الاستلام\n"
        reply += "✅ تحويل بنكي\n\n"
        reply += f"التوصيل: 25 ريال (داخل المدينة)\n\n"
        reply += "تحب اطلبو ليك؟ او عندك سؤال تاني?"
        
        return json.dumps({'reply': reply, 'products': [product], 'html_cards': build_product_card_html(product)})
    
    # ====== 9. الرد الافتراضي ======
    default_reply = RESPONSES_DATA.get('default', {}).get('response', 
        "والله ما فهمت سؤالك 😅\n"
        "عندنا ملابس رجالي ونسائي واحذية.\n"
        "قولي اسم المنتج اللي عاوزو وانا اخدمك.\n\n"
        "تحب اطلبو ليك؟ او عندك سؤال تاني؟")
    return json.dumps({'reply': default_reply, 'products': [], 'html_cards': ''})

@app.route('/api/smart-response', methods=['POST'])
def api_smart_response():
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'رسالة فارغة'}), 400
    
    result = generate_smart_response(user_message)
    parsed = json.loads(result)
    return jsonify(parsed)

# ==================== معالجة الأخطاء ====================
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'خطأ في الخادم'}), 500

# ==================== إقلاع التطبيق ====================
if __name__ == '__main__':
    print("[START] Clothing Store Started!")
    print("[URL] http://localhost:5000")
    print("[ADMIN] http://localhost:5000/admin")
    app.run(debug=True, host='0.0.0.0', port=5000)