// ===== متجر الملابس - JavaScript =====
let cart = JSON.parse(localStorage.getItem('cart')) || [];
let allProducts = [];
let currentCategory = 'all';
let chatInitialized = false;

// ===== التهيئة =====
document.addEventListener('DOMContentLoaded', function() {
    initNavbar();
    loadProducts();
    loadChat();
    updateCartCount();
    setInterval(loadChat, 3000);
    
    const minimized = localStorage.getItem('chatMinimized') === 'true';
    if (minimized) minimizeChat();
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

// ===== الشات =====
async function loadChat() {
    try {
        const res = await fetch('/api/messages');
        const msgs = await res.json();
        displayChat(msgs);
        
        const panel = document.getElementById('chatPanel');
        if (panel?.classList.contains('active') && !chatInitialized && msgs.length === 0) {
            chatInitialized = true;
            await sendAutoGreeting();
        }
    } catch (e) {}
}

async function sendAutoGreeting() {
    try {
        const res = await fetch('/api/bot-reply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: 'سلام' })
        });
        if (res.ok) {
            const data = await res.json();
            const msg = data.reply;
            await fetch('/api/messages/admin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg, session_id: 'default' })
            });
            loadChat();
        }
    } catch (e) {}
}

function displayChat(msgs) {
    const div = document.getElementById('chatMessages');
    if (!div) return;
    
    if (!msgs || msgs.length === 0) {
        div.innerHTML = `<div style="text-align:center;padding:30px;color:var(--text-muted);"><p>💬 لا توجد رسائل</p><p style="font-size:12px;margin-top:8px;">ابدأ المحادثة مع كارم</p></div>`;
        return;
    }
    
    div.innerHTML = msgs.map(m => {
        const isAdmin = m.sender === 'كارم';
        // تحويل النص إلى HTML مع دعم الأسطر الجديدة
        const formattedMsg = (m.message || '').replace(/\n/g, '<br>');
        return `
        <div class="message ${isAdmin ? 'message-admin' : 'message-user'}">
            <div class="message-bubble">
                <div class="message-text">${formattedMsg}</div>
                ${m.html_cards ? `<div class="chat-products-container">${m.html_cards}</div>` : ''}
                <div class="message-time">${m.timestamp ? new Date(m.timestamp).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' }) : ''}</div>
            </div>
        </div>`;
    }).join('');
    
    div.scrollTop = div.scrollHeight;
}

async function toggleChat() {
    const panel = document.getElementById('chatPanel');
    const btn = document.getElementById('chatButton');
    const mini = document.getElementById('chatMini');
    if (!panel) return;
    
    if (mini?.style.display === 'flex') { restoreChat(); return; }
    
    panel.classList.toggle('active');
    if (panel.classList.contains('active')) {
        if (btn) btn.style.display = 'none';
        if (mini) mini.style.display = 'none';
        if (!chatInitialized) { chatInitialized = true; await sendAutoGreeting(); }
        setTimeout(() => {
            const msgs = document.getElementById('chatMessages');
            if (msgs) msgs.scrollTop = msgs.scrollHeight;
        }, 200);
    } else {
        if (btn) btn.style.display = 'flex';
    }
}

function handleChatKeypress(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const text = input?.value.trim();
    if (!text) { showAlert('اكتب الرسالة', 'warning'); return; }
    
    try {
        const res = await fetch('/api/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender: 'زبون', message: text, session_id: 'default' })
        });
        if (res.ok) {
            if (input) input.value = '';
            // رد ذكي مع عرض المنتجات
            try {
                const botRes = await fetch('/api/bot-reply', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                if (botRes.ok) {
                    const data = await botRes.json();
                    const reply = data.reply;
                    const htmlCards = data.html_cards || '';
                    await fetch('/api/messages/admin', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: reply, html_cards: htmlCards, session_id: 'default' })
                    });
                }
            } catch (e) {}
            loadChat();
        }
    } catch (e) {
        showAlert('خطأ في الإرسال', 'error');
    }
}

// ===== تحجيم الشات =====
function minimizeChat() {
    const panel = document.getElementById('chatPanel');
    const btn = document.getElementById('chatButton');
    const mini = document.getElementById('chatMini');
    if (panel) { panel.classList.remove('active', 'maximized'); }
    if (btn) btn.style.display = 'none';
    if (mini) mini.style.display = 'flex';
    localStorage.setItem('chatMinimized', 'true');
}

function maximizeChat() {
    const panel = document.getElementById('chatPanel');
    const btn = document.getElementById('chatButton');
    const mini = document.getElementById('chatMini');
    if (panel) { panel.classList.add('active', 'maximized'); }
    if (btn) btn.style.display = 'none';
    if (mini) mini.style.display = 'none';
    localStorage.setItem('chatMinimized', 'false');
    setTimeout(() => {
        const msgs = document.getElementById('chatMessages');
        if (msgs) msgs.scrollTop = msgs.scrollHeight;
    }, 200);
}

function restoreChat() {
    const panel = document.getElementById('chatPanel');
    const btn = document.getElementById('chatButton');
    const mini = document.getElementById('chatMini');
    if (panel) { panel.classList.add('active'); panel.classList.remove('maximized'); }
    if (btn) btn.style.display = 'none';
    if (mini) mini.style.display = 'none';
    localStorage.setItem('chatMinimized', 'false');
    setTimeout(() => {
        const msgs = document.getElementById('chatMessages');
        if (msgs) msgs.scrollTop = msgs.scrollHeight;
    }, 200);
}

function closeChatWithPrompt() { openModal('exitChatModal'); }
function cancelExitChat() { closeModal('exitChatModal'); }

async function downloadChatAsPDF() {
    try {
        const res = await fetch('/api/messages');
        const msgs = await res.json();
        if (!msgs.length) { showAlert('لا توجد رسائل', 'warning'); return; }
        
        const now = new Date();
        let html = `
        <div style="direction:rtl;font-family:Tajawal,Arial,sans-serif;padding:20px;max-width:600px;margin:0 auto;">
            <div style="text-align:center;margin-bottom:20px;padding-bottom:15px;border-bottom:2px solid #6C5CE7;">
                <h1 style="color:#6C5CE7;font-size:22px;margin:0;">💬 محادثة المتجر</h1>
                <p style="color:#888;font-size:13px;margin:5px 0 0;">${now.toLocaleDateString('ar-SA')}</p>
            </div>`;
        
        msgs.forEach(m => {
            const isAdmin = m.sender === 'كارم';
            const t = m.timestamp ? new Date(m.timestamp).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' }) : '';
            html += `
            <div style="margin-bottom:10px;text-align:${isAdmin ? 'right' : 'left'};">
                <div style="display:inline-block;max-width:80%;padding:10px 14px;border-radius:12px;
                    ${isAdmin ? 'background:linear-gradient(135deg,#6C5CE7,#5A4BD1);color:white;border-bottom-left-radius:4px;' : 'background:#f0f0f0;color:#333;border-bottom-right-radius:4px;'}">
                    <div style="font-size:13px;">${m.message}</div>
                    <div style="font-size:10px;margin-top:4px;opacity:0.7;">${t}</div>
                </div>
            </div>`;
        });
        
        html += `<div style="text-align:center;margin-top:20px;padding-top:15px;border-top:1px solid #ddd;color:#888;font-size:11px;"><p>متجر الملابس © 2026</p></div></div>`;
        
        closeModal('exitChatModal');
        
        const el = document.createElement('div');
        el.innerHTML = html;
        el.style.cssText = 'position:absolute;left:-9999px;top:0;';
        document.body.appendChild(el);
        
        await html2pdf().set({ margin: 10, filename: `chat_${now.getTime()}.pdf`, image: { type: 'jpeg', quality: 0.98 }, html2canvas: { scale: 2, useCORS: true }, jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' } }).from(el).save();
        document.body.removeChild(el);
        showAlert('✅ تم تحميل المحادثة', 'success');
        await clearMessages();
    } catch (e) {
        showAlert('خطأ في التحميل', 'error');
    }
}

async function clearChatAndExit() {
    closeModal('exitChatModal');
    await clearMessages();
    showAlert('🗑️ تم مسح المحادثة', 'info');
}

async function clearMessages() {
    try {
        await fetch('/api/messages', { method: 'DELETE' });
        chatInitialized = false;
        const panel = document.getElementById('chatPanel');
        if (panel) { panel.classList.remove('active', 'maximized'); }
        const btn = document.getElementById('chatButton');
        if (btn) btn.style.display = 'flex';
        const mini = document.getElementById('chatMini');
        if (mini) mini.style.display = 'none';
        localStorage.setItem('chatMinimized', 'false');
        loadChat();
    } catch (e) {}
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
    ['cartModal', 'productModal', 'exitChatModal'].forEach(id => {
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

// حفظ السلة عند الإغلاق
window.addEventListener('beforeunload', saveCart);