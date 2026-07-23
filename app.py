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
            c.execute('''INSERT INTO products (name, description, price, category, image, created_at)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (p['name'], p.get('description', ''), p['price'], p['category'],
                 p['image'], datetime.now().isoformat()))
        conn.commit()
        print(f"[OK] Seeded {len(products_seed)} products")
    else:
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
    return render_template('index.html', products=products)

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

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==================== API المنتجات ====================
@app.route('/api/products')
def api_products():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')
    conn = get_db()
    c = conn.cursor()
    
    if category != 'all' and search:
        c.execute('SELECT * FROM products WHERE category = ? AND (name LIKE ? OR description LIKE ?) ORDER BY id',
                  (category, f'%{search}%', f'%{search}%'))
    elif category != 'all':
        c.execute('SELECT * FROM products WHERE category = ? ORDER BY id', (category,))
    elif search:
        c.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ? ORDER BY id',
                  (f'%{search}%', f'%{search}%'))
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
    
    c.execute('INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, status, items, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
              (name, phone, address, total, 'pending', json.dumps(items), datetime.now().isoformat()))
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
    stock = int(data.get('stock', 0))
    available = 1 if stock > 0 else 0
    if not image:
        image = data.get('image', '')
    if not name or not price:
        return jsonify({'error': 'الاسم والسعر مطلوبان'}), 400
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO products (name, description, price, category, stock, available, image, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (name, description, price, category, stock, available, image, datetime.now().isoformat()))
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
    stock = int(data.get('stock', 0))
    available = 1 if stock > 0 else 0
    if not image:
        image = data.get('image', '')
    
    if image:
        c.execute('''UPDATE products SET name=?, description=?, price=?, category=?, stock=?, available=?, image=? WHERE id=?''',
                  (name, description, price, category, stock, available, image, pid))
    else:
        c.execute('''UPDATE products SET name=?, description=?, price=?, category=?, stock=?, available=? WHERE id=?''',
                  (name, description, price, category, stock, available, pid))
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

# ==================== دوال مساعدة للبوت ====================
PRODUCTS_STATIC = {
    'فستان': [
        {'name':'فستان سهرة احمر', 'price':'35,000', 'image':'/static/images/dress1.jpg'},
        {'name':'فستان كاجوال ابيض', 'price':'28,000', 'image':'/static/images/dress2.jpg'}
    ],
    'تيشرت': [
        {'name':'تيشرت قطن اسود', 'price':'15,000', 'image':'/static/images/tshirt1.jpg'},
        {'name':'تيشرت مطبوع', 'price':'20,000', 'image':'/static/images/tshirt2.jpg'}
    ],
    'بنطلون': [
        {'name':'بنطلون جينز', 'price':'22,000', 'image':'/static/images/jeans1.jpg'}
    ]
}

def get_bot_response(msg):
    """النظام الذكي الجديد - بفهم الجملة كاملة وبحفظ بيانات الزبون"""
    msg = msg.lower()
    name = session.get('name', '')
    
    # حفظ اسم الزبون
    if 'اسمي' in msg:
        session['name'] = msg.split('اسمي')[-1].strip()
        return {'text': f'تشرفت بيك يا {session["name"]} 💚', 'products': []}
    
    # عايز حاجة رخيصة
    if 'عايز' in msg and 'رخيص' in msg:
        cheap = [PRODUCTS_STATIC['تيشرت'][0]]
        return {'text': 'دي ارخص القطع عندنا حاليا 👇', 'products': cheap}
    
    # فستان سهرة - مناسبة
    if 'سهرة' in msg or 'عيد' in msg or 'مناسبة' in msg:
        return {'text': 'دي تشكيلة السهرات الفخمة عندنا', 'products': PRODUCTS_STATIC['فستان']}
    
    # بحث في المنتجات الثابتة
    for key in PRODUCTS_STATIC:
        if key in msg:
            return {'text': f'لقيت ليك {key} ظابطة 👇', 'products': PRODUCTS_STATIC[key]}
    
    # توصيل - لازم يكون قبل السعر عشان جمل زي "التوصيل بكم"
    if any(x in msg for x in ['توصيل', 'شحن']):
        return {'text': 'توصيل امدرمان والخرطوم 3000 جنيه خلال 24 ساعة 🚚 الدفع كاش او بنك', 'products': []}
    
    # اسعار
    if any(x in msg for x in ['سعر', 'بكم']):
        return {'text': 'اسعارنا: تيشرت 15,000 | فستان 28,000 | بنطلون 22,000 جنيه', 'products': []}
    
    # دفع
    if any(x in msg for x in ['دفع', 'بنك', 'كاش']):
        return {'text': 'الدفع كاش عند الاستلام او تحويل بنكي', 'products': []}
    
    # مقاسات
    if any(x in msg for x in ['مقاس', 'size', 's', 'm', 'l', 'xl']):
        return {'text': 'متوفر كل المقاسات من S لحد XXL 👕 قولي المنتج عشان أتأكد ليك', 'products': []}
    
    # تحية - مع الاسم لو موجود
    if any(x in msg for x in ['مرحبا', 'هلا', 'السلام', 'سلام', 'hi', 'hello']):
        greeting = f'وعليكم السلام {name} 👋' if name else 'وعليكم السلام 👋'
        return {'text': f'{greeting} كيف اقدر اخدمك اليوم؟', 'products': []}
    
    # عرض/تخفيض
    if any(x in msg for x in ['عرض', 'تخفيض', 'خصم']):
        return {'text': '🔥 عرض اليوم: اشتري قطعتين والتالتة مجانا!', 'products': []}
    
    # جودة
    if any(x in msg for x in ['خامة', 'جودة', 'اصلي']):
        return {'text': 'كل شغلنا قطن 100% ومستورد. ضمان سنة ✅', 'products': []}
    
    # استبدال
    if any(x in msg for x in ['استبدال', 'مرتجع', 'ترجيع']):
        return {'text': 'مسموح الاستبدال خلال 3 ايام لو في عيب مصنعي 🔄', 'products': []}
    
    # اتصال
    if any(x in msg for x in ['رقم', 'اتصل', 'واتس', 'تلفون']):
        return {'text': '📞 تواصل معانا: 249127599044 واتساب', 'products': []}
    
    # ما فهمت
    return {'text': 'ما فهمت قصدك 😅 ممكن تقول: وريني فساتين, عايز حاجة رخيصة, التوصيل بكم', 'products': []}

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
        c.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ? LIMIT 5',
                  (f'%{search_text}%', f'%{search_text}%'))
        products = c.fetchall()
        
        if not products:
            for term in terms:
                if len(term) > 1:
                    c.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ? LIMIT 3',
                              (f'%{term}%', f'%{term}%'))
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
    products = conn.cursor().execute('SELECT * FROM products WHERE category = ? AND stock > 0', (cat,)).fetchall()
    return [dict(p) for p in products] if products else None

# ==================== النظام الجديد للبوت يقرأ من قاعدة البيانات ====================
def get_bot_reply_with_products(msg):
    """نظام جديد: يقرأ المنتجات من قاعدة البيانات ويرجعها بالشكل text + products"""
    msg = msg.lower().strip()
    
    # تحية
    if msg in ['السلام عليكم', 'سلام', 'عليكم السلام', 'مرحبا', 'هلا', 'hi', 'hello', 'اهلا', 'أهلا']:
        return jsonify({
            'text': 'وعليكم السلام ورحمة الله وبركاته 🌙\nمرحبا بيك في FASHION HUB. كيف اقدر اخدمك؟',
            'products': []
        })
    if any(w in msg for w in ['سلام', 'مرحبا', 'هلا', 'hi', 'hello']):
        return jsonify({
            'text': 'وعليكم السلام 👋 نورت FASHION HUB. كيف اقدر اخدمك؟',
            'products': []
        })
    
    # اسعار
    if any(w in msg for w in ['سعر', 'بكم', 'سعرو', 'price', 'قروش']):
        return jsonify({
            'text': 'اسعارنا: تيشرت 15,000 - 20,000 | فستان 25,000 - 40,000 | بنطلون 18,000 - 30,000 جنيه. عايز سعر منتج معين؟',
            'products': []
        })
    
    # توصيل
    if any(w in msg for w in ['توصيل', 'شحن', 'يصل', 'امدرمان', 'الخرطوم', 'الولايات']):
        return jsonify({
            'text': 'بنوصل امدرمان والخرطوم 3000 جنيه خلال 24 ساعة 🚚 الولايات 5000 جنيه خلال 3 ايام',
            'products': []
        })
    
    # مقاسات
    if any(w in msg for w in ['مقاس', 'size', 's', 'm', 'l', 'xl', 'xxl']):
        return jsonify({
            'text': 'متوفر كل المقاسات من S لحد XXL 👕 وريني المنتج بتأكد ليك المقاس',
            'products': []
        })
    
    # دفع
    if any(w in msg for w in ['دفع', 'بنكك', 'كاش', 'تحويل', 'باي']):
        return jsonify({
            'text': 'متاح: كاش عند الاستلام او تحويل بنك او فوري',
            'products': []
        })
    
    # فساتين - تجيب من قاعدة البيانات
    if any(w in msg for w in ['فستان', 'فساتين', 'dress', 'وريني فساتين']):
        conn = get_db()
        products = conn.cursor().execute("SELECT * FROM products WHERE category = ?", ('نسائي',)).fetchall()
        if products:
            products_list = [dict(p) for p in products]
            return jsonify({
                'text': 'دي احدث الفساتين عندنا 🔥:',
                'products': [{'name': p['name'], 'price': f"{int(p['price']):,}", 'image': p['image']} for p in products_list]
            })
        return jsonify({
            'text': 'عندنا فساتين سهرة، كاجوال، اطفال 🔥 بتبدأ من 25,000. ارسل ليك صور؟',
            'products': []
        })
    
    # رجالي
    if any(w in msg for w in ['رجالي', 'رجال', 'شبابي']):
        conn = get_db()
        products = conn.cursor().execute("SELECT * FROM products WHERE category = ?", ('رجالي',)).fetchall()
        if products:
            products_list = [dict(p) for p in products]
            return jsonify({
                'text': 'الملابس الرجالية المتوفرة 👔:',
                'products': [{'name': p['name'], 'price': f"{int(p['price']):,}", 'image': p['image']} for p in products_list]
            })
        return jsonify({'text': 'قسم الرجالي متوفر فيه قمصان، بناطيل، جواكيت واسعار من 15,000', 'products': []})
    
    # نسائي
    if any(w in msg for w in ['نسائي', 'نساء', 'بنات', 'حريم']):
        conn = get_db()
        products = conn.cursor().execute("SELECT * FROM products WHERE category = ?", ('نسائي',)).fetchall()
        if products:
            products_list = [dict(p) for p in products]
            return jsonify({
                'text': 'الملابس النسائية المتوفرة 👗:',
                'products': [{'name': p['name'], 'price': f"{int(p['price']):,}", 'image': p['image']} for p in products_list]
            })
        return jsonify({'text': 'قسم النسائي متوفر فيه فساتين، عبايات، بلوزات واسعار من 15,000', 'products': []})
    
    # احذية
    if any(w in msg for w in ['احذية', 'حذاء', 'شوز', 'boots', 'sneakers']):
        conn = get_db()
        products = conn.cursor().execute("SELECT * FROM products WHERE category = ?", ('احذية',)).fetchall()
        if products:
            products_list = [dict(p) for p in products]
            return jsonify({
                'text': 'الاحذية المتوفرة عندنا 👟:',
                'products': [{'name': p['name'], 'price': f"{int(p['price']):,}", 'image': p['image']} for p in products_list]
            })
        return jsonify({'text': 'قسم الاحذية متوفر فيه كعب عالي، رياضي، صنادل واسعار من 20,000', 'products': []})
    
    # عبايات وطرح
    if any(w in msg for w in ['عباية', 'طرحة']):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE name LIKE '%عباية%' OR name LIKE '%طرحة%'")
        products = [dict(p) for p in c.fetchall()]
        if products:
            return jsonify({
                'text': 'العبايات والطرح المتوفرة:',
                'products': [{'name': p['name'], 'price': f"{int(p['price']):,}", 'image': p['image']} for p in products]
            })
        return jsonify({'text': 'متوفر عبايات وطرح تركية. الاسعار من 20,000 جنيه', 'products': []})
    
    # بحث عام في قاعدة البيانات
    conn = get_db()
    c = conn.cursor()
    # كلمات للبحث
    keywords_map = {
        'قميص': 'قميص', 'كتان': 'كتان', 'بولو': 'بولو',
        'جينز': 'جينز', 'تيشرت': 'تيشرت', 'هودي': 'هودي',
        'جاكيت': 'جاكيت', 'بلوزة': 'بلوزة', 'بدلة': 'بدلة',
        'تنورة': 'تنورة', 'بلايزر': 'بلايزر', 'حزام': 'حزام',
        'جمبسوت': 'جمبسوت', 'عباية': 'عباية', 'فستان': 'فستان',
    }
    for word, term in keywords_map.items():
        if word in msg:
            c.execute("SELECT * FROM products WHERE (name LIKE ? OR description LIKE ?) AND stock > 0 LIMIT 5",
                      (f'%{term}%', f'%{term}%'))
            products = [dict(p) for p in c.fetchall()]
            if products:
                return jsonify({
                    'text': f'لقيتلك منتجات "{term}" ✅:',
                    'products': [{'name': p['name'], 'price': f"{int(p['price']):,}", 'image': p['image']} for p in products]
                })
    
    # اكسسوارات
    if any(w in msg for w in ['اكسسوارات', 'اكسسوار']):
        conn = get_db()
        products = conn.cursor().execute("SELECT * FROM products WHERE category = ?", ('اكسسوارات',)).fetchall()
        if products:
            products_list = [dict(p) for p in products]
            return jsonify({
                'text': 'الاكسسوارات المتوفرة ⌚:',
                'products': [{'name': p['name'], 'price': f"{int(p['price']):,}", 'image': p['image']} for p in products_list]
            })
        return jsonify({'text': 'قسم الاكسسوارات متوفر فيه احزمة، ساعات، نظارات', 'products': []})
    
    # ردود ثابتة
    if any(w in msg for w in ['خامة', 'قماش', 'جودة', 'اصلي']):
        return jsonify({'text': 'كل شغلنا قطن 100% ومستورد. ضمان سنة ضد عيوب التصنيع', 'products': []})
    if any(w in msg for w in ['عرض', 'تخفيض', 'خصم', 'sale']):
        return jsonify({'text': '🔥 عرض اليوم: اشتري قطعتين والتالتة مجانا. ساري لحد نهاية الاسبوع', 'products': []})
    if any(w in msg for w in ['مرتجع', 'ترجيع', 'استبدال', 'مشكلة']):
        return jsonify({'text': 'مسموح الاستبدال خلال 3 ايام لو في عيب مصنعي. بنرسل ليك مندوب', 'products': []})
    if any(w in msg for w in ['وين', 'محل', 'متجر', 'location']):
        return jsonify({'text': 'نحن متجر الكتروني في امدرمان. البيع اونلاين والتوصيل لكل السودان', 'products': []})
    if any(w in msg for w in ['رقم', 'اتصل', 'تواصل', 'واتس', 'call', 'phone', 'تلفون']):
        return jsonify({'text': '📞 تواصل معانا: 249127599044 واتساب او اتصال. موجودين 9 صباحاً ل 9 مساءً', 'products': []})
    if any(w in msg for w in ['دوام', 'مواعيد', 'مفتوح', 'ساعات']):
        return jsonify({'text': 'شغلنا من 9 الصبح ل 9 المساء كل يوم 📅 الجمعة اجازة', 'products': []})
    if any(w in msg for w in ['اطفال', 'بيبي']):
        return jsonify({'text': 'قسم الاطفال متوفر من عمر سنة ل 12 سنة. الاسعار من 10,000 جنيه', 'products': []})
    
    # البحث بالاسم
    remove_words = ['عاوز', 'عايز', 'دلني', 'وريني', 'شوف', 'ارني', 'اقترح',
                    'عندك', 'في', 'متوفر', 'ال', 'هو', 'دا', 'ده', 'دي',
                    'بكم', 'كام', 'كم', 'شنو', 'ايش', 'ماذا', 'و', 'او', 'من']
    q = msg
    for w in remove_words:
        q = q.replace(w, ' ')
    q = ' '.join(q.split()).strip()
    
    if len(q) >= 2:
        c.execute("SELECT * FROM products WHERE (name LIKE ? OR description LIKE ?) AND stock > 0 LIMIT 5",
                  (f'%{q}%', f'%{q}%'))
        products = [dict(p) for p in c.fetchall()]
        if products:
            return jsonify({
                'text': 'لقيتلك المنتجات دي ✅:',
                'products': [{'name': p['name'], 'price': f"{int(p['price']):,}", 'image': p['image']} for p in products]
            })
    
    # افتراضي
    return jsonify({
        'text': 'ما فهمت سؤالك 😅 قولي عاوز تشوف شنو؟ عندنا تيشرتات، فساتين، بناطيل، عبايات واكسسوارات. او اتصل بينا 249127599044',
        'products': []
    })

# ==================== النظام القديم (getBotReply) مع عرض المنتجات ====================
def getBotReply(msg):
    msg = msg.lower().strip()
    
    # 1. تحية
    if msg == 'السلام عليكم' or msg == 'سلام' or msg == 'عليكم السلام':
        return {'reply': 'وعليكم السلام ورحمة الله وبركاته 🌙\nمرحبا بيك في FASHION HUB. كيف اقدر اخدمك؟', 'products': [], 'html_cards': ''}
    if msg in ['مرحبا', 'هلا', 'hi', 'hello', 'اهلا', 'أهلا']:
        return {'reply': 'وعليكم السلام 👋 نورت FASHION HUB. كيف اقدر اخدمك؟', 'products': [], 'html_cards': ''}
    if any(w in msg for w in ['سلام', 'مرحبا', 'هلا', 'hi', 'hello']):
        return {'reply': 'وعليكم السلام 👋 نورت FASHION HUB. كيف اقدر اخدمك؟', 'products': [], 'html_cards': ''}
    
    # 2. اسعار
    if any(w in msg for w in ['سعر', 'بكم', 'سعرو', 'price', 'قروش']):
        return {'reply': 'اسعارنا: تيشرت 15,000 - 20,000 | فستان 25,000 - 40,000 | بنطلون 18,000 - 30,000 جنيه. عايز سعر منتج معين؟', 'products': [], 'html_cards': ''}
    
    # 3. توصيل
    if any(w in msg for w in ['توصيل', 'شحن', 'يصل', 'امدرمان', 'الخرطوم', 'الولايات']):
        return {'reply': 'بنوصل امدرمان والخرطوم 3000 جنيه خلال 24 ساعة 🚚 الولايات 5000 جنيه خلال 3 ايام', 'products': [], 'html_cards': ''}
    
    # 4. مقاسات
    if any(w in msg for w in ['مقاس', 'size', 's', 'm', 'l', 'xl', 'xxl']):
        return {'reply': 'متوفر كل المقاسات من S لحد XXL 👕 وريني المنتج بتأكد ليك المقاس', 'products': [], 'html_cards': ''}
    
    # 5. دفع
    if any(w in msg for w in ['دفع', 'بنكك', 'كاش', 'تحويل', 'باي']):
        return {'reply': 'متاح: كاش عند الاستلام او تحويل بنك او فوري', 'products': [], 'html_cards': ''}
    
    # 6. منتجات - فساتين
    if any(w in msg for w in ['فستان', 'فساتين', 'dress']):
        products = get_products_by_category('نسائي')
        if products:
            cards = ''.join([product_card_html(p) for p in products])
            reply = "الفساتين المتوفرة عندنا 🔥:\n"
            for p in products:
                reply += f"\n• {p['name']}: {p['price']} ريال"
            reply += "\n\nتحب تشوف تفاصيل اكتر؟"
            return {'reply': reply, 'products': products, 'html_cards': cards}
        return {'reply': 'عندنا فساتين سهرة، كاجوال، اطفال 🔥 بتبدأ من 25,000. ارسل ليك صور؟', 'products': [], 'html_cards': ''}
    
    # 6. منتجات - تيشرتات
    if any(w in msg for w in ['تيشرت', 'بلوزة', 'قميص', 'shirt']):
        products = search_products_in_db(msg)
        if products:
            cards = ''.join([product_card_html(p) for p in products])
            reply = "تيشرتات وبلوزات متوفرة 👕:\n"
            for p in products:
                reply += f"\n• {p['name']}: {p['price']} ريال"
            reply += "\n\nتحب تطلب حاجة؟"
            return {'reply': reply, 'products': products, 'html_cards': cards}
        return {'reply': 'تيشرتات قطن 100% ب 15,000 - 20,000. الوان كتيرة ومقاسات كلها', 'products': [], 'html_cards': ''}
    
    # 6. منتجات - بناطيل
    if any(w in msg for w in ['بنطلون', 'جينز', 'pants', 'jeans']):
        products = search_products_in_db(msg)
        if products:
            cards = ''.join([product_card_html(p) for p in products])
            reply = "البناطيل المتوفرة 👖:\n"
            for p in products:
                reply += f"\n• {p['name']}: {p['price']} ريال"
            reply += "\n\nتحب تطلب حاجة؟"
            return {'reply': reply, 'products': products, 'html_cards': cards}
        return {'reply': 'جينز وكلاسيك ورياضي. السعر من 18,000. رجالي ونسائي', 'products': [], 'html_cards': ''}
    
    # 6. منتجات - عبايات وطرح
    if any(w in msg for w in ['عباية', 'طرحة']):
        products = search_products_in_db(msg)
        if products:
            cards = ''.join([product_card_html(p) for p in products])
            reply = "العبايات والطرح المتوفرة:\n"
            for p in products:
                reply += f"\n• {p['name']}: {p['price']} ريال"
            reply += "\n\nتحب تطلب حاجة؟"
            return {'reply': reply, 'products': products, 'html_cards': cards}
        return {'reply': 'متوفر عبايات وطرح تركية. الاسعار من 20,000 جنيه', 'products': [], 'html_cards': ''}
    
    # 6. منتجات - اطفال
    if any(w in msg for w in ['اطفال', 'بيبي']):
        products = get_products_by_category('اطفال')
        if products:
            cards = ''.join([product_card_html(p) for p in products])
            reply = "ملابس الاطفال المتوفرة 👶:\n"
            for p in products:
                reply += f"\n• {p['name']}: {p['price']} ريال"
            reply += "\n\nتحب تطلب حاجة؟"
            return {'reply': reply, 'products': products, 'html_cards': cards}
        return {'reply': 'قسم الاطفال متوفر من عمر سنة ل 12 سنة. الاسعار من 10,000 جنيه', 'products': [], 'html_cards': ''}
    
    # 7. جودة وخامة
    if any(w in msg for w in ['خامة', 'قماش', 'جودة', 'اصلي']):
        return {'reply': 'كل شغلنا قطن 100% ومستورد. ضمان سنة ضد عيوب التصنيع', 'products': [], 'html_cards': ''}
    
    # 8. عروض
    if any(w in msg for w in ['عرض', 'تخفيض', 'خصم', 'sale']):
        return {'reply': '🔥 عرض اليوم: اشتري قطعتين والتالتة مجانا. ساري لحد نهاية الاسبوع', 'products': [], 'html_cards': ''}
    
    # 9. مرتجع واستبدال
    if any(w in msg for w in ['مرتجع', 'ترجيع', 'استبدال', 'مشكلة']):
        return {'reply': 'مسموح الاستبدال خلال 3 ايام لو في عيب مصنعي. بنرسل ليك مندوب', 'products': [], 'html_cards': ''}
    
    # 10. متجر ومعلومات
    if any(w in msg for w in ['وين', 'محل', 'متجر', 'location']):
        return {'reply': 'نحن متجر الكتروني في امدرمان. البيع اونلاين والتوصيل لكل السودان', 'products': [], 'html_cards': ''}
    
    # 11. رقم/اتصال
    if any(w in msg for w in ['رقم', 'اتصل', 'تواصل', 'واتس', 'call', 'phone', 'تلفون']):
        return {'reply': '📞 تواصل معانا: 249127599044 واتساب او اتصال. موجودين 9 صباحاً ل 9 مساءً', 'products': [], 'html_cards': ''}
    
    # 12. وقت العمل
    if any(w in msg for w in ['دوام', 'مواعيد', 'مفتوح', 'ساعات']):
        return {'reply': 'شغلنا من 9 الصبح ل 9 المساء كل يوم 📅 الجمعة اجازة', 'products': [], 'html_cards': ''}
    
    # 13. بحث عن منتجات - رجالي
    if any(w in msg for w in ['رجالي', 'رجال', 'شبابي']):
        products = get_products_by_category('رجالي')
        if products:
            cards = ''.join([product_card_html(p) for p in products])
            reply = "الملابس الرجالية المتوفرة 👔:\n"
            for p in products:
                reply += f"\n• {p['name']}: {p['price']} ريال"
            reply += "\n\nتحب تطلب حاجة؟"
            return {'reply': reply, 'products': products, 'html_cards': cards}
    
    # 13. بحث عن منتجات - نسائي
    if any(w in msg for w in ['نسائي', 'نساء', 'بنات', 'حريم']):
        products = get_products_by_category('نسائي')
        if products:
            cards = ''.join([product_card_html(p) for p in products])
            reply = "الملابس النسائية المتوفرة 👗:\n"
            for p in products:
                reply += f"\n• {p['name']}: {p['price']} ريال"
            reply += "\n\nتحب تطلب حاجة؟"
            return {'reply': reply, 'products': products, 'html_cards': cards}
    
    # 13. بحث عن منتجات - احذية
    if any(w in msg for w in ['احذية', 'حذاء', 'شوز', 'boots', 'sneakers']):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE name LIKE '%حذاء%' OR name LIKE '%بوت%' OR name LIKE '%صندل%' OR name LIKE '%كعب%'")
        products = [dict(p) for p in c.fetchall()]
        if not products:
            products = get_products_by_category('رجالي') or []
        if products:
            cards = ''.join([product_card_html(p) for p in products])
            reply = "الاحذية المتوفرة عندنا 👟:\n"
            for p in products:
                reply += f"\n• {p['name']}: {p['price']} ريال"
            reply += "\n\nتحب تطلب حاجة؟"
            return {'reply': reply, 'products': products, 'html_cards': cards}
    
    # 14. بحث عام في قاعدة البيانات
    result = search_products_in_db(msg)
    if result:
        cards = ''.join([product_card_html(p) for p in result])
        reply = "لقيتلك المنتجات دي ✅:\n"
        for p in result:
            reply += f"\n• {p['name']}: {p['price']} ريال - {p.get('description','')[:40]}"
        reply += "\n\nتحب تطلب حاجة؟"
        return {'reply': reply, 'products': result, 'html_cards': cards}
    
    # 15. افتراضي
    return {'reply': 'ما فهمت سؤالك 😅 قولي عاوز تشوف شنو؟ عندنا تيشرتات، فساتين، بناطيل، عبايات واكسسوارات. او اتصل بينا 249127599044', 'products': [], 'html_cards': ''}

@app.route('/api/bot-reply', methods=['POST'])
def api_bot_reply():
    data = request.get_json()
    msg = data.get('message', '')
    if not msg:
        return jsonify({'error': 'فارغة'}), 400
    # استخدم النظام الذكي الجديد - بفهم الجملة وبحفظ بيانات الزبون
    result = get_bot_response(msg)
    return jsonify({
        'text': result['text'],
        'products': result['products']
    })

# ==================== الشات الذكي (النظام القديم) ====================
def load_responses():
    path = os.path.join(os.path.dirname(__file__), 'responses.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

RESPONSES = load_responses()

def find_response(message):
    if not RESPONSES:
        return None
    ml = message.lower()
    for key, data in RESPONSES.items():
        if key == 'default':
            continue
        for kw in data.get('keywords', []):
            if kw in ml:
                return data.get('response', '')
    return None

def search_products_db(query):
    conn = get_db()
    c = conn.cursor()
    
    remove_words = ['عاوز', 'عايز', 'دلني', 'وريني', 'شوف', 'ارني', 'اقترح',
                    'عندك', 'في', 'متوفر', 'ال', 'هو', 'دا', 'ده', 'دي',
                    'بكم', 'كام', 'كم']
    q = query
    for w in remove_words:
        q = q.replace(w, ' ')
    q = ' '.join(q.split())
    q = q.strip()
    
    if len(q) < 2:
        return None
    
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
    }
    
    terms = []
    for word in q.split():
        terms.append(keywords.get(word, word))
    
    search_text = ' '.join(terms)
    
    try:
        c.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ? LIMIT 5',
                  (f'%{search_text}%', f'%{search_text}%'))
        products = c.fetchall()
        
        if not products:
            for term in terms:
                if len(term) > 1:
                    c.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ? LIMIT 3',
                              (f'%{term}%', f'%{term}%'))
                    products = c.fetchall()
                    if products:
                        break
        
        if products:
            return [dict(p) for p in products]
    except:
        return None
    return None

def get_products_by_cat(cat):
    conn = get_db()
    products = conn.cursor().execute('SELECT * FROM products WHERE category = ? AND stock > 0', (cat,)).fetchall()
    return [dict(p) for p in products] if products else None

@app.route('/api/smart-response', methods=['POST'])
def api_smart_response():
    data = request.get_json()
    msg = data.get('message', '')
    if not msg:
        return jsonify({'error': 'فارغة'}), 400
    
    ml = msg.lower()
    
    # 1. تحية
    if any(w in ml for w in ['سلام', 'السلام عليكم', 'مرحبا', 'اهلا', 'hi', 'hello']):
        reply = "وعليكم السلام ورحمة الله 👋\nمرحبا بيك في متجرنا 🛍️\nمعاك كارم 😊\n\nعندنا تشكيلة حلوة:\n👔 رجالي: قمصان، بولو، جينز، احذية\n👗 نسائي: فساتين، صنادل، بوت، كعب\n\nقولي عاوز تشوف شنو بالضبط؟\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
        return jsonify({'reply': reply, 'products': [], 'html_cards': ''})
    
    # 2. ردود مسبقة
    r = find_response(msg)
    if r:
        return jsonify({'reply': r, 'products': [], 'html_cards': ''})
    
    # 3. منتجات حسب الفئة
    if any(w in ml for w in ['رجالي', 'رجال', 'شبابي']):
        products = get_products_by_cat('رجالي')
        if products:
            reply = "الملابس الرجالية المتوفرة 👔:\n\n"
            cards = ''
            for p in products:
                cards += product_card_html(p)
                reply += f"- {p['name']}: {p['price']} ريال\n"
            reply += "\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
            return jsonify({'reply': reply, 'products': products, 'html_cards': cards})
    
    if any(w in ml for w in ['نسائي', 'نساء', 'بنات', 'حريم', 'فساتين', 'فستان', 'دريس']):
        products = get_products_by_cat('نسائي')
        if products:
            reply = "الملابس النسائية المتوفرة 👗:\n\n"
            cards = ''
            for p in products:
                cards += product_card_html(p)
                reply += f"- {p['name']}: {p['price']} ريال\n"
            reply += "\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
            return jsonify({'reply': reply, 'products': products, 'html_cards': cards})
    
    if any(w in ml for w in ['احذية', 'حذاء', 'شوز', 'boots', 'sneakers']):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE name LIKE '%حذاء%' OR name LIKE '%بوت%' OR name LIKE '%صندل%' OR name LIKE '%كعب%'")
        products = [dict(p) for p in c.fetchall()]
        if not products:
            products = get_products_by_cat('رجالي') or []
        if products:
            reply = "الاحذية المتوفرة عندنا 👟:\n\n"
            cards = ''
            for p in products:
                cards += product_card_html(p)
                reply += f"- {p['name']}: {p['price']} ريال\n"
            reply += "\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
            return jsonify({'reply': reply, 'products': products, 'html_cards': cards})
    
    # 4. بحث
    result = search_products_db(msg)
    if result:
        p = result[0]
        if p.get('stock', 0) <= 0:
            reply = "المنتج دا حاليا غير متوفر 😅\nاحجزو ليك اول ما يتوفر؟\n\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
            return jsonify({'reply': reply, 'products': [p], 'html_cards': product_card_html(p)})
        
        reply = f"متوفر عندنا ✅\n\nالاسم: {p['name']}\nالسعر: {p['price']} ريال\nالوصف: {p.get('description','')}\nالكمية: {p['stock']} قطعة\n\nطرق الدفع:\n✅ كاش عند الاستلام\n✅ تحويل بنكي\n\nالتوصيل: 25 ريال (داخل المدينة)\n\nتحب اطلبو ليك؟ او عندك سؤال تاني؟"
        return jsonify({'reply': reply, 'products': [p], 'html_cards': product_card_html(p)})
    
    # 5. افتراضي
    default = RESPONSES.get('default', {}).get('response',
        "والله ما فهمت سؤالك 😅\nعندنا ملابس رجالي ونسائي واحذية.\nقولي اسم المنتج اللي عاوزو وانا اخدمك.\n\nتحب اطلبو ليك؟ او عندك سؤال تاني؟")
    return jsonify({'reply': default, 'products': [], 'html_cards': ''})

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