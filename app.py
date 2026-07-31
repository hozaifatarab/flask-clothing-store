"""
متجر ملابس - Clothing Store
تطبيق فلاسك كامل مع لوحة تحكم وشات ذكي
"""
from flask import Flask, render_template, request, jsonify, session, g, redirect, url_for, send_from_directory, flash
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import os
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from products import products as products_seed
from dotenv import load_dotenv

# ==================== الإعدادات ====================
load_dotenv()

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
DATABASE = 'products.db'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fashionhub_secret_2026')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
CORS(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static/images', exist_ok=True)

# ==================== هيكل التصنيفات ====================
CATEGORY_STRUCTURE = {
    'رجالي': {
        'ملابس': ['تيشرتات', 'بناطلين', 'رسمي', 'رياضة'],
        'احذية': ['كاجوال', 'رسمي', 'رياضي', 'شباشب'],
        'عطور': []
    },
    'نسائي': {
        'ملابس': ['فساتين سهرة', 'كاجوال', 'عبايات'],
        'احذية': ['كعب عالي', 'فلات', 'رياضي'],
        'شنط': ['يد', 'ظهر', 'كروس'],
        'عطور ومكياج': []
    },
    'اطفال': {
        'ملابس': [],
        'احذية': []
    }
}

# ==================== قاعدة البيانات ====================
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        price REAL NOT NULL,
        category TEXT NOT NULL DEFAULT 'رجالي',
        subcategory TEXT DEFAULT '',
        type TEXT DEFAULT '',
        stock INTEGER DEFAULT 0,
        available INTEGER DEFAULT 1,
        image TEXT DEFAULT '',
        size TEXT DEFAULT 'قياسي',
        color TEXT DEFAULT 'متنوع',
        created_at TEXT DEFAULT ''
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT DEFAULT '',
        customer_phone TEXT DEFAULT '',
        customer_address TEXT DEFAULT '',
        total_price REAL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        payment_method TEXT DEFAULT 'كاش',
        payment_status TEXT DEFAULT 'pending',
        items TEXT DEFAULT '[]',
        created_at TEXT DEFAULT ''
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT DEFAULT 'default',
        sender TEXT DEFAULT '',
        message TEXT DEFAULT '',
        timestamp TEXT DEFAULT ''
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS admin_credentials (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        username TEXT NOT NULL DEFAULT 'admin',
        password TEXT NOT NULL DEFAULT ''
    )''')
    
    # Admin default
    c.execute('SELECT COUNT(*) as cnt FROM admin_credentials')
    if c.fetchone()['cnt'] == 0:
        hashed = generate_password_hash('admin123')
        c.execute('INSERT INTO admin_credentials (id, username, password) VALUES (1, ?, ?)',
                  ('admin', hashed))
    else:
        # ترقية كلمة المرور الحالية إذا كانت غير مشفرة
        c.execute('SELECT password, username FROM admin_credentials WHERE id = 1')
        row = c.fetchone()
        if row and not row['password'].startswith('scrypt:'):
            new_hash = generate_password_hash(row['password'])
            c.execute('UPDATE admin_credentials SET password = ? WHERE id = 1', (new_hash,))
            print(f"[OK] Upgraded password for user '{row['username']}' to hashed format")
    
    # Seed products
    c.execute('SELECT COUNT(*) as cnt FROM products')
    if c.fetchone()['cnt'] == 0:
        for p in products_seed:
            c.execute('''INSERT INTO products (name, description, price, category, subcategory, type, stock, available, image, size, color, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (p['name'], p.get('description', ''), p['price'], p['category'],
                 p.get('subcategory', ''), p.get('type', ''), p.get('stock', 0), 1 if p.get('stock', 0) > 0 else 0,
                 p['image'], p.get('size', 'قياسي'), p.get('color', 'متنوع'), datetime.now().isoformat()))
        conn.commit()
        print(f"[OK] Seeded {len(products_seed)} products")
    else:
        # التحقق من وجود عمود type وإضافته إذا لم يكن موجوداً
        try:
            c.execute('SELECT type FROM products LIMIT 1')
        except sqlite3.OperationalError:
            c.execute('ALTER TABLE products ADD COLUMN type TEXT DEFAULT ""')
            conn.commit()
            print("[OK] Added 'type' column to existing products table")
        print("[OK] Database already exists")
    
    conn.close()

with app.app_context():
    init_db()

# ==================== دوال مساعدة ====================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_admin_credentials():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT username, password FROM admin_credentials WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper

def get_products(category=None, subcategory=None, ptype=None):
    """جلب المنتجات حسب التصنيفات (1, 2, أو 3 مستويات)"""
    conn = get_db()
    c = conn.cursor()
    
    if category and subcategory and ptype:
        c.execute('''SELECT * FROM products 
                     WHERE category = ? AND subcategory = ? AND type = ? 
                     ORDER BY id''', (category, subcategory, ptype))
    elif category and subcategory:
        c.execute('''SELECT * FROM products 
                     WHERE category = ? AND subcategory = ? 
                     ORDER BY id''', (category, subcategory))
    elif category:
        c.execute('''SELECT * FROM products 
                     WHERE category = ? 
                     ORDER BY id''', (category,))
    else:
        c.execute('SELECT * FROM products ORDER BY id')
    
    return c.fetchall()

def get_page_title(category, subcategory=None, ptype=None):
    """توليد عنوان الصفحة حسب التصنيفات"""
    if category and subcategory and ptype:
        return f'{ptype} - {subcategory} {category}'
    elif category and subcategory:
        return f'{subcategory} {category}'
    elif category:
        return f'قسم {category}'
    return 'جميع المنتجات'

# ==================== التحكم الأساسي ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        env_pass = os.environ.get('ADMIN_PASSWORD')
        credentials = get_admin_credentials()
        
        # التحقق من كلمة السر المشفرة
        if credentials and username == credentials['username']:
            if check_password_hash(credentials['password'], password):
                session['logged_in'] = True
                return redirect(url_for('admin'))
        
        # التحقق من متغير البيئة (للتوافق مع الإصدارات السابقة)
        if env_pass and password == env_pass:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        
        flash('اسم المستخدم أو كلمة السر غير صحيحة')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

@app.context_processor
def inject_user():
    return dict(is_admin=session.get('logged_in', False))

# ==================== الصفحات ====================
@app.route('/')
def home():
    return redirect(url_for('index'))

@app.route('/index')
def index():
    conn = get_db()
    products = conn.cursor().execute('SELECT * FROM products ORDER BY id').fetchall()
    return render_template('index.html', products=products, title='الرئيسية', current_category='all', current_subcategory='', current_type='')

@app.route('/product/<int:pid>')
def product_detail(pid):
    conn = get_db()
    product = conn.cursor().execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()
    if not product:
        return redirect(url_for('home'))
    return render_template('index.html', products=[product])

@app.route('/cart')
def cart():
    return render_template('index.html')

# ===== صفحات الرجالي =====
@app.route('/men')
def men():
    products = get_products(category='رجالي')
    return render_template('index.html', products=products, title='قسم الرجالي', current_category='رجالي', current_subcategory='', current_type='')

@app.route('/men/clothes')
def men_clothes():
    products = get_products(category='رجالي', subcategory='ملابس')
    return render_template('index.html', products=products, title='ملابس رجالية', current_category='رجالي', current_subcategory='ملابس', current_type='')

@app.route('/men/clothes/<ptype>')
def men_clothes_type(ptype):
    products = get_products(category='رجالي', subcategory='ملابس', ptype=ptype)
    return render_template('index.html', products=products, title=f'{ptype} رجالي', current_category='رجالي', current_subcategory='ملابس', current_type=ptype)

@app.route('/men/shoes')
def men_shoes():
    products = get_products(category='رجالي', subcategory='احذية')
    return render_template('index.html', products=products, title='احذية رجالية', current_category='رجالي', current_subcategory='احذية', current_type='')

@app.route('/men/shoes/<ptype>')
def men_shoes_type(ptype):
    products = get_products(category='رجالي', subcategory='احذية', ptype=ptype)
    return render_template('index.html', products=products, title=f'{ptype} رجالي', current_category='رجالي', current_subcategory='احذية', current_type=ptype)

@app.route('/men/perfume')
def men_perfume():
    products = get_products(category='رجالي', subcategory='عطور')
    return render_template('index.html', products=products, title='عطور رجالية', current_category='رجالي', current_subcategory='عطور', current_type='')

# ===== صفحات النسائي =====
@app.route('/women')
def women():
    products = get_products(category='نسائي')
    return render_template('index.html', products=products, title='قسم النسائي', current_category='نسائي', current_subcategory='', current_type='')

@app.route('/women/clothes')
def women_clothes():
    products = get_products(category='نسائي', subcategory='ملابس')
    return render_template('index.html', products=products, title='ملابس نسائية', current_category='نسائي', current_subcategory='ملابس', current_type='')

@app.route('/women/clothes/<ptype>')
def women_clothes_type(ptype):
    products = get_products(category='نسائي', subcategory='ملابس', ptype=ptype)
    return render_template('index.html', products=products, title=f'{ptype} نسائي', current_category='نسائي', current_subcategory='ملابس', current_type=ptype)

@app.route('/women/shoes')
def women_shoes():
    products = get_products(category='نسائي', subcategory='احذية')
    return render_template('index.html', products=products, title='احذية نسائية', current_category='نسائي', current_subcategory='احذية', current_type='')

@app.route('/women/shoes/<ptype>')
def women_shoes_type(ptype):
    products = get_products(category='نسائي', subcategory='احذية', ptype=ptype)
    return render_template('index.html', products=products, title=f'{ptype} نسائي', current_category='نسائي', current_subcategory='احذية', current_type=ptype)

@app.route('/women/bags')
def women_bags():
    products = get_products(category='نسائي', subcategory='شنط')
    return render_template('index.html', products=products, title='شنط نسائية', current_category='نسائي', current_subcategory='شنط', current_type='')

@app.route('/women/bags/<ptype>')
def women_bags_type(ptype):
    products = get_products(category='نسائي', subcategory='شنط', ptype=ptype)
    return render_template('index.html', products=products, title=f'{ptype} نسائي', current_category='نسائي', current_subcategory='شنط', current_type=ptype)

@app.route('/women/perfume')
def women_perfume():
    products = get_products(category='نسائي', subcategory='عطور ومكياج')
    return render_template('index.html', products=products, title='عطور ومكياج نسائي', current_category='نسائي', current_subcategory='عطور ومكياج', current_type='')

# ===== صفحات اطفال =====
@app.route('/kids')
def kids():
    products = get_products(category='اطفال')
    return render_template('index.html', products=products, title='قسم الاطفال', current_category='اطفال', current_subcategory='', current_type='')

@app.route('/kids/clothes')
def kids_clothes():
    products = get_products(category='اطفال', subcategory='ملابس')
    return render_template('index.html', products=products, title='ملابس اطفال', current_category='اطفال', current_subcategory='ملابس', current_type='')

@app.route('/kids/shoes')
def kids_shoes():
    products = get_products(category='اطفال', subcategory='احذية')
    return render_template('index.html', products=products, title='احذية اطفال', current_category='اطفال', current_subcategory='احذية', current_type='')

# ===== الإكسسوارات (تبقى كما هي للتوافق) =====
@app.route('/shoes')
def shoes():
    products = get_products(category='احذية')
    return render_template('index.html', products=products, title='قسم الاحذية', current_category='احذية', current_subcategory='', current_type='')

@app.route('/accessories')
def accessories():
    products = get_products(category='اكسسوارات')
    return render_template('index.html', products=products, title='قسم الاكسسوارات', current_category='اكسسوارات', current_subcategory='', current_type='')

@app.route('/shoes/رياضي')
def shoes_riyadi():
    products = get_products(category='احذية', subcategory='رياضي')
    return render_template('index.html', products=products, title='احذية رياضية', current_category='احذية', current_subcategory='رياضي', current_type='')

@app.route('/shoes/كوتشي')
def shoes_kotchi():
    products = get_products(category='احذية', subcategory='كوتشي')
    return render_template('index.html', products=products, title='كوتشي', current_category='احذية', current_subcategory='كوتشي', current_type='')

@app.route('/shoes/صندل')
def shoes_sandal():
    products = get_products(category='احذية', subcategory='صندل')
    return render_template('index.html', products=products, title='صنادل', current_category='احذية', current_subcategory='صندل', current_type='')

@app.route('/accessories/ساعات')
def acc_watches():
    products = get_products(category='اكسسوارات', subcategory='ساعات')
    return render_template('index.html', products=products, title='ساعات', current_category='اكسسوارات', current_subcategory='ساعات', current_type='')

@app.route('/accessories/نظارات')
def acc_glasses():
    products = get_products(category='اكسسوارات', subcategory='نظارات')
    return render_template('index.html', products=products, title='نظارات', current_category='اكسسوارات', current_subcategory='نظارات', current_type='')

@app.route('/accessories/حقائب')
def acc_bags():
    products = get_products(category='اكسسوارات', subcategory='حقائب')
    return render_template('index.html', products=products, title='حقائب', current_category='اكسسوارات', current_subcategory='حقائب', current_type='')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==================== API المنتجات ====================
@app.route('/api/products')
def api_products():
    category = request.args.get('category', 'all')
    subcategory = request.args.get('subcategory', '')
    ptype = request.args.get('type', '')
    search = request.args.get('search', '')
    conn = get_db()
    c = conn.cursor()
    
    if search:
        c.execute('SELECT * FROM products WHERE (name LIKE ? OR description LIKE ? OR type LIKE ?) ORDER BY id',
                  (f'%{search}%', f'%{search}%', f'%{search}%'))
    elif category != 'all' and subcategory and ptype:
        c.execute('SELECT * FROM products WHERE category = ? AND subcategory = ? AND type = ? ORDER BY id',
                  (category, subcategory, ptype))
    elif category != 'all' and subcategory:
        c.execute('SELECT * FROM products WHERE category = ? AND subcategory = ? ORDER BY id',
                  (category, subcategory))
    elif category != 'all':
        c.execute('SELECT * FROM products WHERE category = ? ORDER BY id', (category,))
    else:
        c.execute('SELECT * FROM products ORDER BY id')
    
    return jsonify([dict(p) for p in c.fetchall()])

@app.route('/api/product/<int:pid>')
def api_product(pid):
    conn = get_db()
    product = conn.cursor().execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()
    if not product:
        return jsonify({'error': 'غير موجود'}), 404
    return jsonify(dict(product))

# ==================== API التصنيفات ====================
@app.route('/api/categories')
def api_categories():
    """إرجاع هيكل التصنيفات بالكامل (للاستخدام في القوائم المنسدلة)"""
    return jsonify(CATEGORY_STRUCTURE)

@app.route('/api/categories/types')
def api_category_types():
    """إرجاع الأنواع حسب القسم والقسم الفرعي"""
    category = request.args.get('category', '')
    subcategory = request.args.get('subcategory', '')
    if category in CATEGORY_STRUCTURE and subcategory in CATEGORY_STRUCTURE[category]:
        return jsonify(CATEGORY_STRUCTURE[category][subcategory])
    return jsonify([])

# ==================== API الشات ====================
@app.route('/api/messages', methods=['GET', 'POST', 'DELETE'])
def api_messages():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute('SELECT * FROM messages ORDER BY timestamp ASC LIMIT 100')
        return jsonify([dict(m) for m in c.fetchall()])
    
    elif request.method == 'POST':
        data = request.get_json()
        sender = data.get('sender', 'زائر').strip()
        message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        if not sender or not message:
            return jsonify({'error': 'الرسالة فارغة'}), 400
        c.execute('INSERT INTO messages (session_id, sender, message, timestamp) VALUES (?, ?, ?, ?)',
                  (session_id, sender, message, datetime.now().isoformat()))
        conn.commit()
        c.execute('SELECT * FROM messages WHERE id = ?', (c.lastrowid,))
        return jsonify(dict(c.fetchone()))
    
    elif request.method == 'DELETE':
        c.execute('DELETE FROM messages')
        conn.commit()
        return jsonify({'success': True})

@app.route('/api/messages/admin', methods=['POST'])
def api_admin_message():
    data = request.get_json()
    message = data.get('message', '').strip()
    session_id = data.get('session_id', 'default')
    html_cards = data.get('html_cards', '')
    if not message:
        return jsonify({'error': 'فارغة'}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO messages (session_id, sender, message, timestamp) VALUES (?, ?, ?, ?)',
              (session_id, 'كارم', message, datetime.now().isoformat()))
    conn.commit()
    c.execute('SELECT * FROM messages WHERE id = ?', (c.lastrowid,))
    msg = dict(c.fetchone())
    if html_cards:
        msg['html_cards'] = html_cards
    return jsonify(msg)

# ==================== API الطلبات ====================
@app.route('/api/orders', methods=['POST'])
def api_create_order():
    data = request.get_json()
    name = data.get('customer_name', '').strip()
    phone = data.get('customer_phone', '').strip()
    address = data.get('customer_address', '').strip()
    items = data.get('items', [])
    total = data.get('total_price', 0)
    
    if not name or not phone or not items:
        return jsonify({'error': 'البيانات ناقصة'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # التحقق من المخزون المتوفر
    for item in items:
        product = c.execute('SELECT stock FROM products WHERE id = ?', (item['id'],)).fetchone()
        if not product:
            return jsonify({'error': f'المنتج رقم {item["id"]} غير موجود'}), 400
        qty = item.get('quantity', 1)
        if product['stock'] < qty:
            return jsonify({'error': f'الكمية المطلوبة من "{item.get("name", "")}" غير متوفرة (المتوفر: {product["stock"]})'}), 400
    
    payment_method = data.get('payment_method', 'كاش')
    payment_status = data.get('payment_status', 'pending')
    
    c.execute('INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, status, payment_method, payment_status, items, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
              (name, phone, address, total, 'pending', payment_method, payment_status, json.dumps(items), datetime.now().isoformat()))
    order_id = c.lastrowid
    
    for item in items:
        c.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (item.get('quantity', 1), item['id']))
    conn.commit()
    
    return jsonify({'success': True, 'order_id': order_id, 'message': f'✅ تم استلام طلبك رقم {order_id}'})

@app.route('/api/orders/<int:oid>')
def api_get_order(oid):
    conn = get_db()
    order = conn.cursor().execute('SELECT * FROM orders WHERE id = ?', (oid,)).fetchone()
    if not order:
        return jsonify({'error': 'غير موجود'}), 404
    d = dict(order)
    d['items'] = json.loads(order['items'])
    return jsonify(d)

# ==================== لوحة التحكم ====================
@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@app.route('/admin_settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    msg = msg_type = None
    if request.method == 'POST':
        username = request.form.get('new_username', '').strip()
        old_pass = request.form.get('old_password', '').strip()
        new_pass = request.form.get('new_password', '').strip()
        if not username or not old_pass or not new_pass:
            msg, msg_type = 'املأ جميع الحقول', 'error'
        else:
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT * FROM admin_credentials WHERE id = 1')
            admin = c.fetchone()
            if not admin:
                msg, msg_type = 'خطأ في النظام', 'error'
            elif not check_password_hash(admin['password'], old_pass):
                msg, msg_type = 'كلمة السر الحالية غير صحيحة', 'error'
            else:
                new_hash = generate_password_hash(new_pass)
                c.execute('UPDATE admin_credentials SET username = ?, password = ? WHERE id = 1', (username, new_hash))
                conn.commit()
                msg, msg_type = 'تم التحديث بنجاح', 'success'
    return render_template('admin_settings.html', message=msg, message_type=msg_type)

# ==================== API الإدارة ====================
@app.route('/api/admin/products', methods=['GET', 'POST'])
@login_required
def api_admin_products():
    if request.method == 'GET':
        conn = get_db()
        products = conn.cursor().execute('SELECT * FROM products ORDER BY id').fetchall()
        return jsonify([dict(p) for p in products])
    
    image = ''
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            parts = filename.rsplit('.', 1)
            filename = f"{parts[0]}_{int(datetime.now().timestamp())}.{parts[1]}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = f'/uploads/{filename}'
    
    data = request.get_json() if request.is_json else request.form
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = float(data.get('price', 0))
    category = data.get('category', 'رجالي')
    subcategory = data.get('subcategory', '').strip()
    ptype = data.get('type', '').strip()
    stock = int(data.get('stock', 0))
    available = 1 if stock > 0 else 0
    if not image:
        image = data.get('image', '')
    if not name or not price:
        return jsonify({'error': 'الاسم والسعر مطلوبان'}), 400
    
    size = data.get('size', 'قياسي').strip()
    color = data.get('color', 'متنوع').strip()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO products (name, description, price, category, subcategory, type, stock, available, image, size, color, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (name, description, price, category, subcategory, ptype, stock, available, image, size, color, datetime.now().isoformat()))
    conn.commit()
    c.execute('SELECT * FROM products WHERE id = ?', (c.lastrowid,))
    return jsonify(dict(c.fetchone()))

@app.route('/api/admin/products/<int:pid>', methods=['PUT', 'DELETE'])
@login_required
def api_admin_product(pid):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute('DELETE FROM products WHERE id = ?', (pid,))
        conn.commit()
        return jsonify({'success': True})
    
    image = ''
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            parts = filename.rsplit('.', 1)
            filename = f"{parts[0]}_{int(datetime.now().timestamp())}.{parts[1]}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = f'/uploads/{filename}'
    
    data = request.get_json() if request.is_json else request.form
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = float(data.get('price', 0))
    category = data.get('category', 'رجالي')
    subcategory = data.get('subcategory', '').strip()
    ptype = data.get('type', '').strip()
    stock = int(data.get('stock', 0))
    available = 1 if stock > 0 else 0
    if not image:
        image = data.get('image', '')
    size = data.get('size', 'قياسي').strip()
    color = data.get('color', 'متنوع').strip()
    
    if image:
        c.execute('''UPDATE products SET name=?, description=?, price=?, category=?, subcategory=?, type=?, stock=?, available=?, image=?, size=?, color=? WHERE id=?''',
                  (name, description, price, category, subcategory, ptype, stock, available, image, size, color, pid))
    else:
        c.execute('''UPDATE products SET name=?, description=?, price=?, category=?, subcategory=?, type=?, stock=?, available=?, size=?, color=? WHERE id=?''',
                  (name, description, price, category, subcategory, ptype, stock, available, size, color, pid))
    conn.commit()
    c.execute('SELECT * FROM products WHERE id = ?', (pid,))
    return jsonify(dict(c.fetchone()))

@app.route('/api/admin/orders')
@login_required
def api_admin_orders():
    conn = get_db()
    orders = conn.cursor().execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    result = []
    for o in orders:
        d = dict(o)
        d['items'] = json.loads(o['items'])
        result.append(d)
    return jsonify(result)

@app.route('/api/admin/orders/<int:oid>/status', methods=['PUT'])
@login_required
def api_update_order_status(oid):
    status = request.get_json().get('status')
    if status not in ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']:
        return jsonify({'error': 'حالة غير صالحة'}), 400
    conn = get_db()
    conn.cursor().execute('UPDATE orders SET status = ? WHERE id = ?', (status, oid))
    conn.commit()
    return jsonify({'success': True})

# ==================== API الدفع عبر الشات ====================
@app.route('/api/chat/checkout', methods=['POST'])
def api_chat_checkout():
    """إنشاء طلب مباشرة من الشات مع طريقة الدفع"""
    data = request.get_json()
    name = data.get('customer_name', '').strip()
    phone = data.get('customer_phone', '').strip()
    address = data.get('customer_address', '').strip()
    items = data.get('items', [])
    total = data.get('total_price', 0)
    payment_method = data.get('payment_method', 'كاش')
    
    if not name or not phone or not items:
        return jsonify({'error': 'البيانات ناقصة'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # التحقق من المخزون
    for item in items:
        product = c.execute('SELECT stock, name FROM products WHERE id = ?', (item['id'],)).fetchone()
        if not product:
            return jsonify({'error': f'المنتج رقم {item["id"]} غير موجود'}), 400
        qty = item.get('quantity', 1)
        if product['stock'] < qty:
            return jsonify({'error': f'الكمية المطلوبة من "{item.get("name", product["name"])}" غير متوفرة (المتوفر: {product["stock"]})'}), 400
    
    payment_status = 'pending'
    if payment_method == 'تحويل بنكي':
        payment_status = 'awaiting_transfer'
    
    c.execute('INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, status, payment_method, payment_status, items, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
              (name, phone, address, total, 'pending', payment_method, payment_status, json.dumps(items), datetime.now().isoformat()))
    order_id = c.lastrowid
    
    for item in items:
        c.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (item.get('quantity', 1), item['id']))
    conn.commit()
    
    # رسالة تأكيد حسب طريقة الدفع
    if payment_method == 'كاش':
        msg = f'✅ تم تأكيد طلبك رقم {order_id}!\n💰 طريقة الدفع: كاش عند الاستلام\n📦 سيتم التواصل معاك خلال 24 ساعة'
    elif payment_method == 'تحويل بنكي':
        msg = f'✅ تم تأكيد طلبك رقم {order_id}!\n🏦 طريقة الدفع: تحويل بنكي\n📱 بنكك: 123456789 (حساب FASHION HUB)\n📸 يرجى إرسال صورة الإيداع عبر الواتساب 249127599044'
    else:
        msg = f'✅ تم تأكيد طلبك رقم {order_id}!\n💰 طريقة الدفع: {payment_method}\n📦 سيتم التواصل معاك قريباً'
    
    return jsonify({
        'success': True,
        'order_id': order_id,
        'message': msg,
        'order': {
            'id': order_id,
            'customer_name': name,
            'customer_phone': phone,
            'customer_address': address,
            'total_price': total,
            'payment_method': payment_method,
            'payment_status': payment_status,
            'items': json.dumps(items)
        }
    })

# ==================== دوال مساعدة للبوت ====================

def product_card_html(p):
    """توليد HTML لبطاقة منتج واحدة"""
    return f'''
    <div class="chat-product-card">
        <img src="{p.get('image','')}" alt="{p.get('name','')}" class="chat-product-img" onerror="this.src='https://via.placeholder.com/80?text=?'">
        <div class="chat-product-info">
            <div class="chat-product-name">{p.get('name','')}</div>
            <div class="chat-product-desc">{p.get('description','')[:60]}{'...' if len(p.get('description','')) > 60 else ''}</div>
            <div class="chat-product-price">{p.get('price',0)} ريال</div>
            <div class="chat-product-stock">{'✅ متوفر' if p.get('stock',0) > 0 else '❌ غير متوفر'}</div>
        </div>
    </div>'''

def search_products_in_db(query):
    """البحث عن منتجات في قاعدة البيانات"""
    conn = get_db()
    c = conn.cursor()
    
    # كلمات يجب إزالتها من الاستعلام
    remove_words = ['عاوز', 'عايز', 'دلني', 'وريني', 'شوف', 'ارني', 'اقترح',
                    'عندك', 'في', 'متوفر', 'ال', 'هو', 'دا', 'ده', 'دي',
                    'بكم', 'كام', 'كم', 'شنو', 'ايش', 'ماذا', 'و', 'او', 'من']
    q = query
    for w in remove_words:
        q = q.replace(w, ' ')
    q = ' '.join(q.split())
    q = q.strip()
    
    if len(q) < 2:
        return None
    
    # كلمات مفتاحية للمنتجات
    keywords = {
        'قميص': 'قميص', 'كتان': 'كتان', 'رمادي': 'رمادي', 'بولو': 'بولو',
        'اسود': 'اسود', 'جينز': 'جينز', 'ازرق': 'ازرق', 'رسمي': 'رسمي',
        'ابيض': 'ابيض', 'حذاء': 'حذاء', 'بني': 'بني', 'رياضي': 'رياضي',
        'فستان': 'فستان', 'احمر': 'احمر', 'زفاف': 'زفاف', 'سهرة': 'سهرة',
        'صيفي': 'صيفي', 'مشجر': 'مشجر', 'عمل': 'عمل', 'اوفيس': 'عمل',
        'بوت': 'بوت', 'صندل': 'صندل', 'كعب': 'كعب', 'عالي': 'عالي',
        'رجالي': 'رجالي', 'نسائي': 'نسائي', 'شبابي': 'رجالي', 'بنات': 'نسائي',
        'دريس': 'فستان', 'شوز': 'حذاء', 'هودي': 'هودي', 'تيشرت': 'تيشرت',
        'جاكيت': 'جاكيت', 'بلوزة': 'بلوزة', 'عباية': 'عباية', 'بدلة': 'بدلة',
        'تنورة': 'تنورة', 'بلايزر': 'بلايزر', 'حزام': 'حزام', 'جمبسوت': 'جمبسوت',
        'اطفال': 'اطفال', 'بيبي': 'اطفال', 'ولادي': 'رجالي', 'حريمي': 'نسائي',
    }
    
    terms = []
    for word in q.split():
        terms.append(keywords.get(word, word))
    
    search_text = ' '.join(terms)
    
    try:
        c.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ? OR type LIKE ? LIMIT 5',
                  (f'%{search_text}%', f'%{search_text}%', f'%{search_text}%'))
        products = c.fetchall()
        
        if not products:
            for term in terms:
                if len(term) > 1:
                    c.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ? OR type LIKE ? LIMIT 3',
                              (f'%{term}%', f'%{term}%', f'%{term}%'))
                    products = c.fetchall()
                    if products:
                        break
        
        if products:
            return [dict(p) for p in products]
    except:
        return None
    return None

def get_products_by_category(cat):
    """جلب المنتجات حسب الفئة"""
    conn = get_db()
    products = conn.cursor().execute('SELECT * FROM products WHERE category = ? ORDER BY id', (cat,)).fetchall()
    return [dict(p) for p in products] if products else None

# ==================== النظام الجديد للبوت (الرئيسي) ====================
@app.route('/api/chat', methods=['POST'])
def api_chat():
    """النظام الموحد للشات - يقرأ من قاعدة البيانات ويعرض المنتجات بالصور والبيانات"""
    data = request.get_json()
    msg = data.get('message', '')
    if not msg:
        return jsonify({'error': 'فارغة'}), 400
    
    msg_lower = msg.lower().strip()
    conn = get_db()
    c = conn.cursor()
    
    # 1. تحية
    if any(w in msg_lower for w in ['السلام عليكم', 'سلام', 'مرحبا', 'هلا', 'اهلا', 'أهلا', 'hi', 'hello']):
        return jsonify({
            'text': 'وعليكم السلام ورحمة الله وبركاته 🌙\nمرحبا بيك في FASHION HUB 🛍️\nمعاك كارم 😊\n\nعندنا تشكيلة حلوة:\n👔 رجالي: قمصان، بولو، جينز، بدل\n👗 نسائي: فساتين، عبايات، بلوزات\n👟 احذية: كعب عالي، رياضي، صنادل\n⌚ اكسسوارات\n\nقولي عاوز تشوف شنو بالضبط؟',
            'products': []
        })
    
    # 2. ردود ثابتة (معلومات المتجر) - مرتبة حسب طول الكلمة المفتاحية (الأطول أولاً)
    static_responses_raw = {
        'توصيل': 'بنوصل امدرمان والخرطوم 3000 جنيه خلال 24 ساعة 🚚 الولايات 5000 جنيه خلال 3 ايام',
        'شحن': 'بنوصل امدرمان والخرطوم 3000 جنيه خلال 24 ساعة 🚚 الولايات 5000 جنيه خلال 3 ايام',
        'بكم التوصيل': 'بنوصل امدرمان والخرطوم 3000 جنيه خلال 24 ساعة 🚚 الولايات 5000 جنيه خلال 3 ايام',
        'سعر': 'اسعارنا: تيشرت 15,000 - 20,000 | فستان 25,000 - 40,000 | بنطلون 18,000 - 30,000 جنيه. عايز سعر منتج معين؟',
        'بكم': 'اسعارنا: تيشرت 15,000 - 20,000 | فستان 25,000 - 40,000 | بنطلون 18,000 - 30,000 جنيه. عايز سعر منتج معين؟',
        'سعرو': 'اسعارنا: تيشرت 15,000 - 20,000 | فستان 25,000 - 40,000 | بنطلون 18,000 - 30,000 جنيه. عايز سعر منتج معين؟',
        'مقاس': 'متوفر كل المقاسات من S لحد XXL 👕 وريني المنتج بتأكد ليك المقاس',
        'دفع': 'متاح: كاش عند الاستلام او تحويل بنك او فوري 💳',
        'بنكك': 'متاح: كاش عند الاستلام او تحويل بنك او فوري 💳',
        'تحويل': 'متاح: كاش عند الاستلام او تحويل بنك او فوري 💳',
        'خامة': 'كل شغلنا قطن 100% ومستورد. ضمان سنة ضد عيوب التصنيع ✅',
        'جودة': 'كل شغلنا قطن 100% ومستورد. ضمان سنة ضد عيوب التصنيع ✅',
        'اصلي': 'كل شغلنا قطن 100% ومستورد. ضمان سنة ضد عيوب التصنيع ✅',
        'عرض': '🔥 عرض اليوم: اشتري قطعتين والتالتة مجانا. ساري لحد نهاية الاسبوع',
        'خصم': '🔥 عرض اليوم: اشتري قطعتين والتالتة مجانا. ساري لحد نهاية الاسبوع',
        'مرتجع': 'مسموح الاستبدال خلال 3 ايام لو في عيب مصنعي. بنرسل ليك مندوب 🔄',
        'استبدال': 'مسموح الاستبدال خلال 3 ايام لو في عيب مصنعي. بنرسل ليك مندوب 🔄',
        'وين': 'نحن متجر الكتروني في امدرمان. البيع اونلاين والتوصيل لكل السودان 📍',
        'محل': 'نحن متجر الكتروني في امدرمان. البيع اونلاين والتوصيل لكل السودان 📍',
        'رقم': '📞 تواصل معانا: 249127599044 واتساب او اتصال. موجودين 9 صباحاً ل 9 مساءً',
        'واتس': '📞 تواصل معانا: 249127599044 واتساب او اتصال. موجودين 9 صباحاً ل 9 مساءً',
        'اتصل': '📞 تواصل معانا: 249127599044 واتساب او اتصال. موجودين 9 صباحاً ل 9 مساءً',
        'دوام': 'شغلنا من 9 الصبح ل 9 المساء كل يوم 📅 الجمعة اجازة',
        'مواعيد': 'شغلنا من 9 الصبح ل 9 المساء كل يوم 📅 الجمعة اجازة',
        'اطفال': 'قسم الاطفال متوفر من عمر سنة ل 12 سنة. الاسعار من 10,000 جنيه',
        'بيبي': 'قسم الاطفال متوفر من عمر سنة ل 12 سنة. الاسعار من 10,000 جنيه',
    }
    
    # ترتيب حسب طول الكلمة (الأطول أولاً) لتجنب المشاكل مثل "بكم التوصيل" تطابق "بكم" قبل "توصيل"
    static_responses = dict(sorted(static_responses_raw.items(), key=lambda x: len(x[0]), reverse=True))
    
    for keyword, response in static_responses.items():
        if keyword in msg_lower:
            return jsonify({'text': response, 'products': []})
    
    # 3. البحث عن منتجات حسب القسم
    category_keywords = {
        'رجالي': 'رجالي', 'رجال': 'رجالي', 'شبابي': 'رجالي', 'ولادي': 'رجالي',
        'نسائي': 'نسائي', 'نساء': 'نسائي', 'بنات': 'نسائي', 'حريم': 'نسائي', 'حريمي': 'نسائي',
        'احذية': 'احذية', 'حذاء': 'احذية', 'شوز': 'احذية',
        'اكسسوارات': 'اكسسوارات', 'اكسسوار': 'اكسسوارات',
    }
    
    for keyword, cat in category_keywords.items():
        if keyword in msg_lower:
            products = get_products_by_category(cat)
            if products:
                for p in products:
                    if isinstance(p.get('price'), (int, float)):
                        p['price_text'] = f"{int(p['price']):,}"
                    else:
                        p['price_text'] = str(p.get('price', 0))
                if cat == 'رجالي':
                    text = 'الملابس الرجالية المتوفرة 👔:'
                elif cat == 'نسائي':
                    text = 'الملابس النسائية المتوفرة 👗:'
                elif cat == 'احذية':
                    text = 'الاحذية المتوفرة عندنا 👟:'
                else:
                    text = 'الاكسسوارات المتوفرة ⌚:'
                return jsonify({'text': text, 'products': products})
            else:
                return jsonify({'text': f'قسم {cat} متوفر فيه تشكيلة واسعة. اسعارنا من 15,000 جنيه', 'products': []})
    
    # 4. البحث بكلمة مفتاحية للمنتج
    product_keywords = {
        'فستان': 'فستان', 'فساتين': 'فستان', 'دريس': 'فستان',
        'تيشرت': 'تيشرت', 'بلوزة': 'بلوزة', 'قميص': 'قميص',
        'بنطلون': 'بنطلون', 'جينز': 'جينز', 'بناطيل': 'بنطلون',
        'عباية': 'عباية', 'عبايات': 'عباية', 'طرحة': 'طرحة',
        'جاكيت': 'جاكيت', 'هودي': 'هودي', 'بدلة': 'بدلة',
        'تنورة': 'تنورة', 'بلايزر': 'بلايزر', 'جمبسوت': 'جمبسوت',
        'حزام': 'حزام', 'بوت': 'بوت', 'صندل': 'صندل',
        'كعب': 'كعب', 'بولو': 'بولو', 'كتان': 'كتان',
    }
    
    for keyword, term in product_keywords.items():
        if keyword in msg_lower:
            c.execute("SELECT * FROM products WHERE (name LIKE ? OR description LIKE ? OR color LIKE ? OR size LIKE ? OR type LIKE ?) AND stock > 0 LIMIT 6",
                      (f'%{term}%', f'%{term}%', f'%{term}%', f'%{term}%', f'%{term}%'))
            products = [dict(p) for p in c.fetchall()]
            if products:
                for p in products:
                    if isinstance(p.get('price'), (int, float)):
                        p['price_text'] = f"{int(p['price']):,}"
                    else:
                        p['price_text'] = str(p.get('price', 0))
                return jsonify({
                    'text': f'لقيتلك منتجات "{term}" ✅:',
                    'products': products
                })
    
    # 5. بحث عام في قاعدة البيانات
    remove_words = ['عاوز', 'عايز', 'دلني', 'وريني', 'شوف', 'ارني', 'اقترح',
                    'عندك', 'في', 'متوفر', 'ال', 'هو', 'دا', 'ده', 'دي',
                    'بكم', 'كام', 'كم', 'شنو', 'ايش', 'ماذا', 'و', 'او', 'من']
    q = msg_lower
    for w in remove_words:
        q = q.replace(w, ' ')
    q = ' '.join(q.split()).strip()
    
    if len(q) >= 2:
        c.execute("SELECT * FROM products WHERE (name LIKE ? OR description LIKE ? OR color LIKE ? OR size LIKE ? OR type LIKE ?) AND stock > 0 LIMIT 5",
                  (f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%'))
        products = [dict(p) for p in c.fetchall()]
        if products:
            for p in products:
                if isinstance(p.get('price'), (int, float)):
                    p['price_text'] = f"{int(p['price']):,}"
                else:
                    p['price_text'] = str(p.get('price', 0))
            return jsonify({
                'text': 'لقيتلك المنتجات دي ✅:',
                'products': products
            })
    
    # 6. افتراضي - ما فهمت
    return jsonify({
        'text': 'ما فهمت سؤالك 😅 قولي عاوز تشوف شنو؟\n\nعندنا:\n👔 رجالي (قمصان، تيشرتات، بناطيل، بدل)\n👗 نسائي (فساتين، عبايات، بلوزات)\n👟 احذية (كعب عالي، رياضي، صنادل)\n⌚ اكسسوارات\nاو اتصل بينا 249127599044',
        'products': []
    })

# ==================== معالجة الأخطاء ====================
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'خطأ في الخادم'}), 500

# ==================== الإطلاق ====================
if __name__ == '__main__':
    print("=" * 40)
    print("Clothing Store - FASHION HUB")
    print(f"http://localhost:5000")
    print(f"http://localhost:5000/admin")
    print("=" * 40)
    app.run(debug=True, host='0.0.0.0', port=5000)