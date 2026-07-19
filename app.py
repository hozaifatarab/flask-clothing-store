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
from products import products as products_seed
from dotenv import load_dotenv

# ==================== الإعدادات ====================
load_dotenv()

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
DATABASE = 'products.db'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'store-secret-key-2026')
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
        password TEXT NOT NULL DEFAULT 'admin123'
    )''')
    
    # Admin default
    c.execute('SELECT COUNT(*) as cnt FROM admin_credentials')
    if c.fetchone()['cnt'] == 0:
        c.execute('INSERT INTO admin_credentials (id, username, password) VALUES (1, ?, ?)',
                  ('admin', 'admin123'))
    
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

def get_admin_password():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT password FROM admin_credentials WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row['password'] if row else None

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
        password = request.form.get('password', '')
        env_pass = os.environ.get('ADMIN_PASSWORD')
        db_pass = get_admin_password()
        if password == env_pass or password == db_pass:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        flash('كلمة السر غير صحيحة')
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
    if not message:
        return jsonify({'error': 'فارغة'}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO messages (session_id, sender, message, timestamp) VALUES (?, ?, ?, ?)',
              (session_id, 'كارم', message, datetime.now().isoformat()))
    conn.commit()
    c.execute('SELECT * FROM messages WHERE id = ?', (c.lastrowid,))
    return jsonify(dict(c.fetchone()))

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
            elif admin['password'] != old_pass:
                msg, msg_type = 'كلمة السر الحالية غير صحيحة', 'error'
            else:
                c.execute('UPDATE admin_credentials SET username = ?, password = ? WHERE id = 1', (username, new_pass))
                conn.commit()
                msg, msg_type = 'تم التحديث بنجاح', 'success'
    return render_template('admin_settings.html', message=msg, message_type=msg_type)

# ==================== API الإدارة ====================
@app.route('/api/admin/products', methods=['GET', 'POST'])
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
def api_update_order_status(oid):
    status = request.get_json().get('status')
    if status not in ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']:
        return jsonify({'error': 'حالة غير صالحة'}), 400
    conn = get_db()
    conn.cursor().execute('UPDATE orders SET status = ? WHERE id = ?', (status, oid))
    conn.commit()
    return jsonify({'success': True})

# ==================== الشات الذكي ====================
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
        q = q.replace(w, '')
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

def product_card_html(p):
    return f'''
    <div style="display:flex;align-items:flex-start;background:white;border-radius:12px;padding:12px;box-shadow:0 2px 8px rgba(0,0,0,0.1);gap:12px;margin-top:8px;direction:rtl;">
        <img src="{p.get('image','')}" alt="{p.get('name','')}" style="width:80px;height:80px;object-fit:cover;border-radius:10px;flex-shrink:0;" onerror="this.src='https://via.placeholder.com/80?text=?'">
        <div style="flex:1;">
            <div style="font-weight:bold;font-size:14px;margin-bottom:4px;">{p.get('name','')}</div>
            <div style="color:#D32F2F;font-weight:bold;font-size:15px;margin-bottom:4px;">{p.get('price',0)} ريال</div>
            <div style="font-size:11px;color:#666;line-height:1.4;">{p.get('description','')}</div>
            <div style="font-size:11px;margin-top:4px;">{"✅ متوفر" if p.get('stock',0) > 0 else "❌ غير متوفر"}</div>
        </div>
    </div>'''

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