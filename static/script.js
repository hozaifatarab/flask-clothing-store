// ===== متجر الملابس - JavaScript =====
let cart = JSON.parse(localStorage.getItem('cart')) || [];
let allProducts = [];
let currentCategory = 'all';

// ===== التهيئة =====
document.addEventListener('DOMContentLoaded', function() {
    initNavbar();
    loadProducts();
    initChat();
    updateCartCount();
});

// ===== النافبار =====
function initNavbar() {
    const toggle = document.getElementById('navToggle');
    const menu = document.getElementById('navMenu');
    if (!toggle || !menu) return;
    
    toggle.addEventListener('click', () => {
        toggle.classList.toggle('active');
        menu.classList.toggle('active');
    });
    
    menu.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            toggle.classList.remove('active');
            menu.classList.remove('active');
        });
    });
    
    document.addEventListener('click', e => {
        if (!toggle.contains(e.target) && !menu.contains(e.target)) {
            toggle.classList.remove('active');
            menu.classList.remove('active');
        }
    });
}

// ===== تحميل المنتجات =====
async function loadProducts(category = 'all', search = '') {
    try {
        let url = '/api/products';
        const params = [];
        if (category && category !== 'all') params.push(`category=${encodeURIComponent(category)}`);
        if (search) params.push(`search=${encodeURIComponent(search)}`);
        if (params.length) url += '?' + params.join('&');
        
        const res = await fetch(url);
        allProducts = await res.json();
        displayProducts(allProducts);
    } catch (e) {
        console.error('Error:', e);
    }
}

function displayProducts(products) {
    const grid = document.getElementById('productsGrid');
    if (!grid) return;
    
    if (!products || products.length === 0) {
        grid.innerHTML = `<div class="empty-state"><div class="empty-state-icon">😞</div><p>لا توجد منتجات</p></div>`;
        return;
    }
    
    grid.innerHTML = products.map(p => {
        const inStock = p.stock > 0;
        return `
        <div class="product-card">
            <div class="product-img-wrap">
                <img src="${p.image || ''}" alt="${p.name}" onerror="this.src='https://via.placeholder.com/300?text=?'">
                ${p.stock > 5 ? '<span class="product-badge badge-new">جديد</span>' : ''}
            </div>
            <div class="product-body">
                <div class="product-name">${p.name}</div>
                <div class="product-desc">${p.description || ''}</div>
                <div class="product-meta">
                    <span class="meta-tag">📐 ${p.size || 'قياسي'}</span>
                    <span class="meta-tag">🎨 ${p.color || 'متنوع'}</span>
                </div>
                <div class="product-price">${p.price} ريال</div>
                <div class="product-stock ${inStock ? 'stock-ok' : 'stock-out'}">
                    ${inStock ? '✅ متوفر (' + p.stock + ')' : '❌ غير متوفر'}
                </div>
                <div class="product-actions">
                    <button class="btn-details" onclick="viewDetails(${p.id})">📋 تفاصيل</button>
                    <button class="btn-cart" onclick="addToCart(${p.id})" ${!inStock ? 'disabled' : ''}>🛒 أضف</button>
                </div>
            </div>
        </div>`;
    }).join('');
}

// ===== بحث وتصفية =====
function searchProducts() {
    const q = document.getElementById('searchInput').value.trim();
    const filtered = q ? allProducts.filter(p => 
        p.name.includes(q) || (p.description || '').includes(q)
    ) : allProducts;
    displayProducts(filtered);
}

function filterCategory(cat) {
    currentCategory = cat;
    document.querySelectorAll('.cat-pill').forEach(p => p.classList.toggle('active', p.dataset.cat === cat));
    document.getElementById('searchInput').value = '';
    loadProducts(cat === 'all' ? 'all' : cat, '');
}

// ===== تفاصيل المنتج =====
async function viewDetails(pid) {
    try {
        const res = await fetch(`/api/product/${pid}`);
        const p = await res.json();
        
        const detail = document.getElementById('productDetail');
        if (!detail) return;
        
        const inStock = p.stock > 0;
        detail.innerHTML = `
        <div class="product-detail-wrap">
            <div class="detail-img">
                <img src="${p.image || ''}" alt="${p.name}" onerror="this.src='https://via.placeholder.com/400?text=?'">
            </div>
            <div class="detail-info">
                <h2>${p.name}</h2>
                <div class="detail-rating">⭐⭐⭐⭐⭐ (4.8/5)</div>
                <div class="detail-price">${p.price} ريال</div>
                <div class="detail-desc">${p.description || ''}</div>
                <div class="detail-specs">
                    <div class="spec-row"><span class="spec-label">الفئة</span><span class="spec-value">${p.category}</span></div>
                    <div class="spec-row"><span class="spec-label">الحجم</span><span class="spec-value">${p.size || 'قياسي'}</span></div>
                    <div class="spec-row"><span class="spec-label">اللون</span><span class="spec-value">${p.color || 'متنوع'}</span></div>
                    <div class="spec-row"><span class="spec-label">المخزون</span><span class="spec-value">${p.stock} قطعة</span></div>
                    <div class="spec-row"><span class="spec-label">الحالة</span><span class="spec-value">${inStock ? '✅ متوفر' : '❌ غير متوفر'}</span></div>
                </div>
                <div class="detail-btns">
                    <button class="btn-add-cart" onclick="addToCart(${p.id}); closeModal('productModal')" ${!inStock ? 'disabled' : ''}>🛒 أضف للسلة</button>
                    <button class="btn-wishlist" onclick="showAlert('✅ تمت الإضافة للمفضلة', 'success')">❤️ مفضلة</button>
                </div>
            </div>
        </div>`;
        
        openModal('productModal');
    } catch (e) {
        showAlert('خطأ في تحميل التفاصيل', 'error');
    }
}

// ===== السلة =====
function addToCart(pid) {
    const p = allProducts.find(x => x.id === pid);
    if (!p) { showAlert('المنتج غير موجود', 'error'); return; }
    if (p.stock <= 0) { showAlert('غير متوفر', 'error'); return; }
    
    const item = cart.find(x => x.id === pid);
    if (item) {
        if (item.quantity < p.stock) item.quantity++;
        else { showAlert('الكمية القصوى', 'warning'); return; }
    } else {
        cart.push({ id: p.id, name: p.name, price: p.price, quantity: 1, size: p.size || 'قياسي', color: p.color || 'متنوع' });
    }
    
    saveCart();
    updateCartCount();
    showAlert(`✅ تمت إضافة ${p.name}`, 'success');
}

function saveCart() { localStorage.setItem('cart', JSON.stringify(cart)); }

function updateCartCount() {
    const count = cart.reduce((t, i) => t + i.quantity, 0);
    document.querySelectorAll('.cart-count, #cartBadge').forEach(el => { if (el) el.textContent = count; });
}

function openCart() {
    displayCart();
    openModal('cartModal');
}

function closeCart() { closeModal('cartModal'); }

function displayCart() {
    const div = document.getElementById('cartItems');
    if (!div) return;
    
    if (cart.length === 0) {
        div.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🛒</div><p>السلة فارغة</p></div>`;
        const sec = document.getElementById('checkoutSection');
        if (sec) sec.style.display = 'none';
        return;
    }
    
    const sec = document.getElementById('checkoutSection');
    if (sec) sec.style.display = 'block';
    
    div.innerHTML = cart.map((item, i) => `
        <div class="cart-item">
            <div>
                <div class="cart-item-name">${item.name}</div>
                <div class="cart-item-detail">📐 ${item.size} | 🎨 ${item.color}</div>
                <div class="cart-item-price">${item.price} ريال</div>
            </div>
            <div class="cart-qty">
                <button class="qty-btn" onclick="updateQty(${i}, -1)">−</button>
                <span style="min-width:28px;text-align:center;font-weight:700;">${item.quantity}</span>
                <button class="qty-btn" onclick="updateQty(${i}, 1)">+</button>
            </div>
            <button class="cart-remove" onclick="removeItem(${i})">🗑️</button>
        </div>
    `).join('');
    
    updateTotal();
}

function updateQty(i, change) {
    const p = allProducts.find(x => x.id === cart[i].id);
    if (!p) return;
    const newQty = cart[i].quantity + change;
    if (newQty > 0 && newQty <= p.stock) {
        cart[i].quantity = newQty;
        saveCart();
        updateCartCount();
        displayCart();
    }
}

function removeItem(i) {
    cart.splice(i, 1);
    saveCart();
    updateCartCount();
    displayCart();
}

function updateTotal() {
    const total = cart.reduce((s, i) => s + i.price * i.quantity, 0);
    const el = document.getElementById('cartTotal');
    if (el) el.textContent = total.toFixed(0);
    const sub = document.getElementById('subtotal');
    if (sub) sub.textContent = total.toFixed(0) + ' ريال';
    const count = document.getElementById('itemCount');
    if (count) count.textContent = cart.reduce((s, i) => s + i.quantity, 0);
}

async function checkoutCart() {
    const name = document.getElementById('customerName')?.value.trim();
    const phone = document.getElementById('customerPhone')?.value.trim();
    const address = document.getElementById('customerEmail')?.value.trim() || '';
    
    if (!name || !phone) { showAlert('يرجى إدخال الاسم والهاتف', 'error'); return; }
    if (cart.length === 0) { showAlert('السلة فارغة', 'error'); return; }
    
    const total = cart.reduce((s, i) => s + i.price * i.quantity, 0);
    
    try {
        const res = await fetch('/api/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_name: name, customer_phone: phone,
                customer_address: address, items: cart, total_price: total
            })
        });
        const data = await res.json();
        if (res.ok) {
            showAlert(data.message, 'success');
            cart = []; saveCart(); updateCartCount(); closeCart();
            ['customerName','customerPhone','customerEmail'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
        } else showAlert(data.error, 'error');
    } catch (e) {
        showAlert('خطأ في الاتصال', 'error');
    }
}

// ===== النوافذ المنبثقة =====
function openModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.add('active');
}

function closeModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.remove('active');
}

// إغلاق المودال بالضغط خارجها
document.addEventListener('click', function(e) {
    ['cartModal', 'productModal'].forEach(id => {
        if (e.target.id === id) closeModal(id);
    });
});

// ===== التنبيهات =====
function showAlert(msg, type = 'info') {
    const existing = document.querySelector('.alert');
    if (existing) existing.remove();
    
    const a = document.createElement('div');
    a.className = `alert alert-${type}`;
    a.textContent = msg;
    document.body.appendChild(a);
    
    setTimeout(() => {
        a.style.opacity = '0';
        a.style.transition = '0.3s';
        setTimeout(() => a.remove(), 300);
    }, 3000);
}

// ===== الشات الذكي (واجهة أمامية بالكامل) =====
function initChat() {
    const chatButton = document.getElementById('chat-button');
    const chatContainer = document.getElementById('chat-container');
    const sendBtn = document.getElementById('send-btn');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');

    if (!chatButton || !chatContainer) return;

    // فتح وقفل الشات
    chatButton.onclick = () => {
        chatContainer.style.display = chatContainer.style.display === 'flex' ? 'none' : 'flex';
        if (chatContainer.style.display === 'flex') {
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    };

    // اضافة رسالة للشات
    function addMessage(text, sender) {
        const msg = document.createElement('div');
        msg.style.padding = '10px 14px';
        msg.style.margin = '8px 5px';
        msg.style.borderRadius = '12px';
        msg.style.maxWidth = '80%';
        msg.style.background = sender === 'user' ? '#007BFF' : '#2a2a3f';
        msg.style.alignSelf = sender === 'user' ? 'flex-end' : 'flex-start';
        msg.style.color = 'white';
        msg.style.fontSize = '14px';
        msg.innerText = text;
        chatBox.appendChild(msg);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // الرد الذكي
    function getBotResponse(message) {
        message = message.toLowerCase();

        if (message.includes('سعر') || message.includes('بكم') || message.includes('السعر')) {
            return '💰 اسعارنا بتبدا من 15 الف جنيه سوداني. تحب تشوف اي قسم؟ نسائي، رجالي، احذية؟';
        } else if (message.includes('توصيل') || message.includes('بتوصلو')) {
            return '🚚 ايوا عندنا توصيل داخل الخرطوم وامدرمان وبحري. التوصيل 5 الف جنيه. الاستلام خلال 24 ساعة';
        } else if (message.includes('فستان') || message.includes('فساتين')) {
            return '👗 عندنا تشكيلة فساتين سهرة وكاجوال جديدة. تحب ارسل ليك صور ولا مقاس معين؟';
        } else if (message.includes('مقاس')) {
            return '📏 المقاسات المتوفرة: S, M, L, XL, XXL. وريني المنتج والمقاس العايزو';
        } else if (message.includes('حذاء') || message.includes('جزمة')) {
            return '👟 متوفر احذية رجالية ونسائية واطفال. المقاسات من 36 لحد 45';
        } else if (message.includes('شكرا') || message.includes('تسلم')) {
            return 'العفو 😊 في خدمتك في اي وقت';
        } else {
            return 'ما فهمت قصدك 😅 ممكن تسألني عن: السعر، التوصيل، فساتين، مقاسات، احذية';
        }
    }

    // ارسال الرسالة
    sendBtn.onclick = () => {
        const message = userInput.value.trim();
        if (message === '') return;
        addMessage(message, 'user');
        userInput.value = '';
        setTimeout(() => {
            addMessage(getBotResponse(message), 'bot');
        }, 600);
    };

    // ارسال بزر Enter
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendBtn.click();
    });
}

// حفظ السلة عند الإغلاق
window.addEventListener('beforeunload', saveCart);