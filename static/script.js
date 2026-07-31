// ===== متجر الملابس - JavaScript =====
let cart = JSON.parse(localStorage.getItem('cart')) || [];
let allProducts = [];
let currentCategory = 'all';
let isChatMinimized = false;
let isChatMaximized = false;

// ===== التهيئة =====
document.addEventListener('DOMContentLoaded', function() {
    initNavbar();
    // تحديد القسم الحالي من مسار الصفحة
    const path = window.location.pathname;
    let initialCategory = 'all';
    if (path === '/men') initialCategory = 'رجالي';
    else if (path === '/women') initialCategory = 'نسائي';
    else if (path === '/shoes') initialCategory = 'احذية';
    else if (path === '/accessories') initialCategory = 'اكسسوارات';
    
    // تفعيل زر القسم المناسب
    document.querySelectorAll('.cat-pill').forEach(p => {
        p.classList.toggle('active', p.dataset.cat === initialCategory || (initialCategory === 'all' && p.dataset.cat === 'all'));
    });
    
    loadProducts(initialCategory);
    currentCategory = initialCategory;
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
        const catBadge = p.category ? `<span class="cat-tag cat-${p.category}">${p.category}</span>` : '';
        const subcatBadge = p.subcategory ? `<span class="cat-tag cat-sub">${p.subcategory}</span>` : '';
        const typeBadge = p.type ? `<span class="cat-tag cat-type">${p.type}</span>` : '';
        const categoriesHtml = (catBadge || subcatBadge || typeBadge) ? `<div class="product-categories">${catBadge}${subcatBadge}${typeBadge}</div>` : '';
        return `
        <div class="product-card">
            <div class="product-img-wrap">
                <img src="${p.image || ''}" alt="${p.name}" onerror="this.src='https://via.placeholder.com/300?text=?'">
                ${p.stock > 5 ? '<span class="product-badge badge-new">جديد</span>' : ''}
            </div>
            <div class="product-body">
                <div class="product-name">${p.name}</div>
                <div class="product-desc">${p.description || ''}</div>
                ${categoriesHtml}
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
                    <button class="btn-buy" onclick="buyNow(${p.id})" ${!inStock ? 'disabled' : ''}>💳 شراء الآن</button>
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

// ===== تصفية حسب القسم الفرعي والنوع =====
function filterSubcategory(category, subcategory) {
    currentCategory = category;
    // تحديث حالة أزرار الأقسام
    document.querySelectorAll('.cat-pill').forEach(p => p.classList.toggle('active', p.dataset.cat === category));
    // تفعيل/إلغاء تفعيل أزرار الفئات الفرعية
    document.querySelectorAll('.subcat-pill').forEach(p => {
        p.classList.toggle('active', p.textContent.trim() === (subcategory || 'الكل') || (!subcategory && p.textContent.includes('الكل')));
    });
    document.getElementById('searchInput').value = '';
    // إعادة تحميل المنتجات مع القسم والقسم الفرعي
    if (subcategory) {
        loadProducts(category, '');
        // تصفية محلية بعد التحميل
        setTimeout(() => {
            const filtered = allProducts.filter(p => p.category === category && p.subcategory === subcategory);
            displayProducts(filtered);
        }, 200);
    } else {
        loadProducts(category, '');
    }
}

function filterType(category, subcategory, ptype) {
    document.getElementById('searchInput').value = '';
    if (ptype) {
        loadProducts(category, '');
        setTimeout(() => {
            const filtered = allProducts.filter(p => p.category === category && p.subcategory === subcategory && p.type === ptype);
            displayProducts(filtered);
        }, 200);
    } else if (subcategory) {
        filterSubcategory(category, subcategory);
    }
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
                    <div class="spec-row"><span class="spec-label">القسم</span><span class="spec-value">${p.category}</span></div>
                    ${p.subcategory ? `<div class="spec-row"><span class="spec-label">القسم الفرعي</span><span class="spec-value">${p.subcategory}</span></div>` : ''}
                    ${p.type ? `<div class="spec-row"><span class="spec-label">النوع</span><span class="spec-value">${p.type}</span></div>` : ''}
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
    // إظهار/إخفاء شارة السلة
    const badge = document.getElementById('cartBadge');
    if (badge) {
        if (count > 0) {
            badge.style.display = 'flex';
            badge.textContent = count;
        } else {
            badge.style.display = 'none';
        }
    }
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
    const address = document.getElementById('customerAddress')?.value.trim() || '';
    
    if (!name || !phone) { showAlert('يرجى إدخال الاسم والهاتف', 'error'); return; }
    if (cart.length === 0) { showAlert('السلة فارغة', 'error'); return; }
    
    // قراءة طريقة الدفع المحددة
    const paymentMethod = document.querySelector('input[name="cartPaymentMethod"]:checked')?.value || 'كاش';
    const total = cart.reduce((s, i) => s + i.price * i.quantity, 0);
    
    try {
        const res = await fetch('/api/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_name: name, customer_phone: phone,
                customer_address: address, items: cart, total_price: total,
                payment_method: paymentMethod
            })
        });
        const data = await res.json();
        if (res.ok) {
            // رسالة تأكيد حسب طريقة الدفع
            let msg = data.message;
            if (paymentMethod === 'تحويل بنكي') {
                msg += '\n📱 بنكك: 123456789 (حساب FASHION HUB)\n📸 أرسل صورة الإيداع على واتساب 249127599044';
            }
            showAlert(`✅ تم تأكيد طلبك رقم ${data.order_id}!`, 'success');
            cart = []; saveCart(); updateCartCount(); closeCart();
            ['customerName','customerPhone','customerAddress'].forEach(id => {
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

// ===== الشات الذكي (النظام الموحد) =====
function initChat() {
    const chatButton = document.getElementById('chat-button');
    const chatPanel = document.getElementById('chatPanel');
    const chatMessages = document.getElementById('chatMessages');
    const messageInput = document.getElementById('messageInput');
    const chatMini = document.getElementById('chatMini');

    if (!chatPanel || !chatMessages) return;

    // رسالة ترحيبية
    addBotMessage('وعليكم السلام ورحمة الله وبركاته 🌙\nمرحبا بيك في FASHION HUB 🛍️\nمعاك كارم 😊\n\nعندنا تشكيلة حلوة:\n👔 رجالي (قمصان، بولو، جينز، بدل)\n👗 نسائي (فساتين، عبايات، بلوزات)\n👟 احذية (كعب عالي، رياضي، صنادل)\n⌚ اكسسوارات\n\nقولي عاوز تشوف شنو بالضبط؟');
}

function toggleChat() {
    const panel = document.getElementById('chatPanel');
    const btn = document.getElementById('chat-button');
    const mini = document.getElementById('chatMini');
    
    if (panel.classList.contains('active')) {
        panel.classList.remove('active');
        btn.style.display = 'flex';
        mini.style.display = 'none';
    } else {
        panel.classList.add('active');
        panel.classList.remove('maximized');
        btn.style.display = 'none';
        mini.style.display = 'none';
        isChatMinimized = false;
        isChatMaximized = false;
    }
}

function minimizeChat() {
    const panel = document.getElementById('chatPanel');
    const mini = document.getElementById('chatMini');
    
    panel.classList.remove('active');
    mini.style.display = 'flex';
    const btn = document.getElementById('chat-button');
    if (btn) btn.style.display = 'none';
    isChatMinimized = true;
}

function maximizeChat() {
    const panel = document.getElementById('chatPanel');
    panel.classList.toggle('maximized');
    isChatMaximized = !isChatMaximized;
}

function restoreChat() {
    const panel = document.getElementById('chatPanel');
    const mini = document.getElementById('chatMini');
    
    panel.classList.add('active');
    mini.style.display = 'none';
    const btn = document.getElementById('chat-button');
    if (btn) btn.style.display = 'none';
    isChatMinimized = false;
}

function closeChatWithPrompt() {
    openModal('exitChatModal');
}

function cancelExitChat() {
    closeModal('exitChatModal');
}

async function downloadChatAsPDF() {
    const messages = document.getElementById('chatMessages');
    if (!messages || messages.children.length === 0) {
        showAlert('💬 لا توجد رسائل للتحميل', 'warning');
        closeModal('exitChatModal');
        return;
    }
    
    try {
        const element = document.createElement('div');
        element.style.padding = '20px';
        element.style.background = '#fff';
        element.style.color = '#000';
        element.style.fontFamily = 'Tajawal, sans-serif';
        element.style.direction = 'rtl';
        element.innerHTML = '<h2 style="text-align:center;color:#6C5CE7;margin-bottom:20px;">💬 محادثة FASHION HUB</h2>';
        
        const chatMessages = document.getElementById('chatMessages');
        const msgs = chatMessages.querySelectorAll('.message');
        msgs.forEach(msg => {
            const isAdmin = msg.classList.contains('message-admin');
            const text = msg.querySelector('.message-text')?.innerText || '';
            const products = msg.querySelector('.chat-products-container');
            const time = msg.querySelector('.message-time')?.innerText || '';
            
            const div = document.createElement('div');
            div.style.cssText = `margin:10px 0;padding:12px;border-radius:10px;background:${isAdmin ? '#6C5CE7' : '#f0f0f0'};color:${isAdmin ? '#fff' : '#000'};text-align:${isAdmin ? 'right' : 'left'};`;
            div.innerHTML = `<div style="font-weight:700;margin-bottom:4px;">${isAdmin ? '🤖 كارم' : '🙋 أنت'}</div><div>${text}</div>${time ? `<div style="font-size:10px;opacity:0.6;margin-top:4px;">${time}</div>` : ''}`;
            
            if (products) {
                const cards = products.querySelectorAll('.chat-product-card');
                cards.forEach(card => {
                    const img = card.querySelector('img')?.src || '';
                    const name = card.querySelector('.chat-product-name')?.innerText || '';
                    const price = card.querySelector('.chat-product-price')?.innerText || '';
                    const stock = card.querySelector('.chat-product-stock')?.innerText || '';
                    const pdiv = document.createElement('div');
                    pdiv.style.cssText = 'margin:8px 0;padding:8px;border:1px solid #ddd;border-radius:8px;display:flex;gap:10px;';
                    pdiv.innerHTML = `<div style="font-weight:700;">${name}</div><div style="color:#e94560;font-weight:700;">${price}</div><div>${stock}</div>`;
                    div.appendChild(pdiv);
                });
            }
            element.appendChild(div);
        });
        
        element.innerHTML += '<div style="text-align:center;margin-top:20px;color:#888;font-size:12px;">© 2026 FASHION HUB - جميع الحقوق محفوظة</div>';
        
        const opt = {
            margin: [10, 10, 10, 10],
            filename: 'chat_fashion_hub.pdf',
            html2canvas: { scale: 2 },
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
        };
        
        await html2pdf().set(opt).from(element).save();
        showAlert('✅ تم تحميل المحادثة بنجاح', 'success');
        clearChatAndExit();
    } catch (e) {
        console.error('PDF Error:', e);
        showAlert('❌ خطأ في تحميل PDF', 'error');
    }
}

function clearChatAndExit() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) chatMessages.innerHTML = '';
    chatHistory = [];
    closeModal('exitChatModal');
    minimizeChat();
    showAlert('🗑️ تم مسح المحادثة', 'info');
}

// ===== وظائف الشات الأساسية =====
function addUserMessage(text) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message message-user';
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = `<div class="message-text">${escapeHtml(text)}</div>`;
    
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = getCurrentTime();
    
    bubble.appendChild(time);
    msgDiv.appendChild(bubble);
    chatMessages.appendChild(msgDiv);
    scrollChatToBottom();
}

function addBotMessage(text, products = []) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message message-admin';
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = `<div class="message-text">${escapeHtml(text)}</div>`;
    
    // عرض المنتجات كبطاقات
    if (products && products.length > 0) {
        const container = document.createElement('div');
        container.className = 'chat-products-container';
        
        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'chat-product-card';
            
            const priceDisplay = p.price_text || (typeof p.price === 'number' ? parseInt(p.price).toLocaleString() : p.price || '0');
            const stockStatus = p.stock > 0 ? '✅ متوفر' : '❌ غير متوفر';
            const desc = (p.description || '').substring(0, 60) + ((p.description || '').length > 60 ? '...' : '');
            const imageUrl = p.image || '';
            
            const sizeText = p.size || 'قياسي';
            const colorText = p.color || 'متنوع';
            card.innerHTML = `
                <img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(p.name || '')}" class="chat-product-img" onerror="this.src='https://via.placeholder.com/80?text=?'">
                <div class="chat-product-info">
                    <div class="chat-product-name">${escapeHtml(p.name || '')}</div>
                    <div class="chat-product-desc">${escapeHtml(desc)}</div>
                    <div class="chat-product-meta">📐 ${escapeHtml(sizeText)} | 🎨 ${escapeHtml(colorText)}</div>
                    <div class="chat-product-price">${escapeHtml(priceDisplay)} ريال</div>
                    <div class="chat-product-stock">${stockStatus}</div>
                </div>
            `;
            
            card.style.cursor = 'pointer';
            card.onclick = () => {
                if (p.id) viewDetails(p.id);
            };
            
            // Add buy button for each product card
            const buyBtn = document.createElement('button');
            buyBtn.className = 'chat-buy-btn';
            buyBtn.innerHTML = '💳 شراء الآن';
            buyBtn.onclick = (e) => {
                e.stopPropagation();
                buyFromChat(p.id);
            };
            container.appendChild(buyBtn);
            
            container.appendChild(card);
        });
        
        bubble.appendChild(container);
    }
    
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = getCurrentTime();
    
    bubble.appendChild(time);
    msgDiv.appendChild(bubble);
    chatMessages.appendChild(msgDiv);
    scrollChatToBottom();
}

function addTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const indicator = document.createElement('div');
    indicator.id = 'typingIndicator';
    indicator.className = 'message message-admin';
    indicator.innerHTML = `
        <div class="message-bubble" style="background:#e8e8e8;color:#666;font-size:14px;">
            <span style="display:flex;align-items:center;gap:8px;">
                <span style="display:inline-block;animation:typingAnim 1.4s infinite;">.</span>
                <span style="display:inline-block;animation:typingAnim 1.4s 0.2s infinite;">.</span>
                <span style="display:inline-block;animation:typingAnim 1.4s 0.4s infinite;">.</span>
                جاري الكتابة...
            </span>
        </div>`;
    chatMessages.appendChild(indicator);
    scrollChatToBottom();
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

async function sendMsg() {
    const input = document.getElementById('messageInput');
    const msg = input.value.trim();
    if (!msg) return;
    
    input.value = '';
    addUserMessage(msg);
    
    // مؤشر الكتابة
    addTypingIndicator();
    
    try {
        const lower = msg.trim().toLowerCase();
        
        // التحقق من نية الشراء / الدفع
        const buyIntent = /^(عاوز|عايز|ابي|اريد|بدي|شراء|اشتري|طلب|اطلب|دفع)\s/i.test(lower) || 
                          /(شراء|اشتري|طلب|اطلب|دفع|كاش|تحويل)/i.test(lower);
        
        // التحقق من وجود بيانات دفع معلقة (بعد اختيار طريقة الدفع)
        if (window._chatPaymentData && window._chatPaymentData.step === 'awaiting_info') {
            removeTypingIndicator();
            // توقع إدخال: الاسم، الهاتف، العنوان
            const parts = msg.split(/[,،\n]+/).map(s => s.trim()).filter(s => s);
            let name = '', phone = '', address = '';
            
            if (parts.length >= 2) {
                name = parts[0];
                phone = parts[1];
                address = parts.length >= 3 ? parts[2] : '';
            } else {
                // محاولة استخراج رقم الهاتف
                const phoneMatch = msg.match(/(\d{7,15})/);
                if (phoneMatch) {
                    phone = phoneMatch[1];
                    // الباقي يعتبر اسم
                    name = msg.replace(phoneMatch[0], '').replace(/[,،\n]+/g, ' ').trim();
                } else {
                    addBotMessage('❌ يرجى إدخال الاسم ورقم الهاتف.\nمثال: أحمد محمد، 0912345678', []);
                    return;
                }
            }
            
            if (!name || !phone) {
                addBotMessage('❌ يرجى إدخال الاسم ورقم الهاتف.\nمثال: أحمد محمد، 0912345678', []);
                return;
            }
            
            const pd = window._chatPaymentData;
            await submitChatOrder(name, phone, address, pd.paymentMethod, pd.items);
            return;
        }
        
        if (buyIntent && cart.length === 0) {
            // إذا كان ينوي الشراء لكن السلة فارغة، اسأله عاوز يشوف شنو
            removeTypingIndicator();
            addBotMessage('✅ تقدر تطلب من هنا!\n\n📦 أولاً اختار المنتجات اللي عاوزها:\n'
                + '1. اكتب اسم المنتج اللي عاوزه (مثلاً: قميص، فستان)\n'
                + '2. أو اكتب اسم القسم (رجالي، نسائي، احذية)\n'
                + '3. أو تصفح المنتجات من فوق 👆\n\n'
                + 'وبعد ما تختار، هتظهر المنتجات وتقدر تضيفها للسلة 🛒\n'
                + 'وبعدين أقدر أساعدك في الدفع 💳', []);
            return;
        }
        
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });
        
        const data = await res.json();
        removeTypingIndicator();
        
        if (data.text) {
            // إذا ذكر الدفع، أظهر خيارات الدفع
            if (/(دفع|طريقة الدفع|كيف ادفع|شلون ادفع|ايش طرق)/i.test(msg)) {
                showPaymentOptions();
                return;
            }
            addBotMessage(data.text, data.products || []);
        } else if (data.reply) {
            // دعم التوافق مع النظام القديم
            if (/(دفع|طريقة الدفع|كيف ادفع|شلون ادفع|ايش طرق)/i.test(msg)) {
                showPaymentOptions();
                return;
            }
            addBotMessage(data.reply, data.products || []);
        }
    } catch (e) {
        removeTypingIndicator();
        addBotMessage('❌ عذرا، حدث خطأ في الاتصال. حاول مرة أخرى');
    }
}

// ===== الدفع داخل الشات =====
let chatCheckoutItems = [];

function showPaymentOptions() {
    const cartItems = JSON.parse(localStorage.getItem('cart')) || [];
    if (cartItems.length === 0) {
        addBotMessage('⚠️ السلة فاضية!\nأضف منتجات للسلة أولاً 🛒\nاكتب اسم المنتج اللي عاوزه.', []);
        return;
    }
    
    chatCheckoutItems = cartItems;
    const total = cartItems.reduce((s, i) => s + i.price * i.quantity, 0);
    const itemsList = cartItems.map(i => `• ${i.name} x${i.quantity} = ${(i.price * i.quantity).toFixed(0)} ريال`).join('\n');
    
    addBotMessage(
        `🛍️ طلبك:\n${itemsList}\n\n💰 الإجمالي: ${total.toFixed(0)} ريال\n\nاختر طريقة الدفع المناسبة 👇`,
        []
    );
    
    // إظهار أزرار الدفع
    setTimeout(() => {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        const paymentDiv = document.createElement('div');
        paymentDiv.className = 'message message-admin';
        paymentDiv.innerHTML = `
            <div class="message-bubble" style="background:transparent;padding:0;max-width:100%;">
                <div class="chat-payment-options">
                    <button class="chat-pay-btn pay-cash" onclick="startChatCheckout('كاش')">
                        <span class="pay-icon">💰</span>
                        <span class="pay-label">كاش عند الاستلام</span>
                        <span class="pay-desc">ادفع عندما تستلم الطلب</span>
                    </button>
                    <button class="chat-pay-btn pay-bank" onclick="startChatCheckout('تحويل بنكي')">
                        <span class="pay-icon">🏦</span>
                        <span class="pay-label">تحويل بنكي</span>
                        <span class="pay-desc">حوّل على حساب المتجر</span>
                    </button>
                    <button class="chat-pay-btn pay-fawry" onclick="startChatCheckout('فوري')">
                        <span class="pay-icon">💳</span>
                        <span class="pay-label">فوري</span>
                        <span class="pay-desc">ادفع عبر فوري</span>
                    </button>
                </div>
            </div>
        `;
        chatMessages.appendChild(paymentDiv);
        scrollChatToBottom();
    }, 500);
}

function startChatCheckout(paymentMethod) {
    if (chatCheckoutItems.length === 0) {
        addBotMessage('⚠️ لا توجد منتجات في السلة للشراء.', []);
        return;
    }
    
    const total = chatCheckoutItems.reduce((s, i) => s + i.price * i.quantity, 0);
    
    addBotMessage(
        `✅ اخترت: ${paymentMethod}\n\n📋 أدخل بياناتك:\n(الاسم ورقم الهاتف)\n\nمثال:\n"أحمد محمد، 0912345678، الخرطوم"`,
        []
    );
    
    // تخزين البيانات مؤقتاً لانتظار إدخال المستخدم
    window._chatPaymentData = { paymentMethod, items: chatCheckoutItems, total, step: 'awaiting_info' };
}

async function submitChatOrder(name, phone, address, paymentMethod, items) {
    const total = items.reduce((s, i) => s + i.price * i.quantity, 0);
    
    try {
        const res = await fetch('/api/chat/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_name: name,
                customer_phone: phone,
                customer_address: address,
                items: items,
                total_price: total,
                payment_method: paymentMethod
            })
        });
        
        const data = await res.json();
        
        if (res.ok) {
            // إفراغ السلة
            cart = [];
            saveCart();
            updateCartCount();
            window._chatPaymentData = null;
            
            addBotMessage(data.message, []);
            
            if (paymentMethod === 'تحويل بنكي') {
                setTimeout(() => {
                    addBotMessage('📸 بعد ما تعمل التحويل، أرسل صورة الإيصال على الواتساب: 249127599044', []);
                }, 1000);
            }
        } else {
            addBotMessage(`❌ ${data.error}`, []);
        }
    } catch (e) {
        addBotMessage('❌ عذراً، حدث خطأ في الاتصال. حاول مرة أخرى', []);
    }
}

// ===== الشراء المباشر (Buy Now) =====
let buyCurrentQty = 1;

function buyNow(pid) {
    const p = allProducts.find(x => x.id === pid);
    if (!p) { showAlert('المنتج غير موجود', 'error'); return; }
    if (p.stock <= 0) { showAlert('غير متوفر', 'error'); return; }
    
    const content = document.getElementById('buyModalContent');
    if (!content) return;
    
    const inStock = p.stock > 0;
    content.innerHTML = `
        <div class="buy-direct-wrap">
            <div class="buy-product-summary">
                <img src="${p.image || ''}" alt="${p.name}" onerror="this.src='https://via.placeholder.com/80?text=?'" class="buy-product-img">
                <div>
                    <div class="buy-product-name">${p.name}</div>
                    <div class="buy-product-price">${p.price} ريال</div>
                    <div class="buy-product-stock ${inStock ? 'stock-ok' : 'stock-out'}">${inStock ? '✅ متوفر' : '❌ غير متوفر'}</div>
                </div>
            </div>
            <div class="buy-form">
                <div class="buy-form-row">
                    <label>الاسم الكامل <span style="color:red;">*</span></label>
                    <input type="text" id="buyName" class="input-field" placeholder="اسمك الكامل" required>
                </div>
                <div class="buy-form-row">
                    <label>رقم الهاتف <span style="color:red;">*</span></label>
                    <input type="text" id="buyPhone" class="input-field" placeholder="رقم الواتساب أو الاتصال" required>
                </div>
                <div class="buy-form-row">
                    <label>العنوان</label>
                    <input type="text" id="buyAddress" class="input-field" placeholder="المدينة والمنطقة">
                </div>
                <div class="buy-form-row">
                    <label>الكمية</label>
                    <div class="buy-qty-selector">
                        <button class="qty-btn" onclick="changeBuyQty(-1)">−</button>
                        <span id="buyQtyDisplay" style="min-width:28px;text-align:center;font-weight:700;">1</span>
                        <button class="qty-btn" onclick="changeBuyQty(1)">+</button>
                    </div>
                </div>
                <div class="buy-form-row">
                    <label style="display:block;font-size:13px;font-weight:600;color:var(--text-muted);margin-bottom:4px;">💳 طريقة الدفع</label>
                    <div class="buy-payment-options">
                        <label class="payment-option" style="flex:1;">
                            <input type="radio" name="buyPaymentMethod" value="كاش" checked>
                            <span class="payment-option-content" style="flex-direction:row;gap:6px;">
                                <span class="payment-option-icon">💰</span>
                                <span class="payment-option-label" style="font-size:12px;">كاش</span>
                            </span>
                        </label>
                        <label class="payment-option" style="flex:1;">
                            <input type="radio" name="buyPaymentMethod" value="تحويل بنكي">
                            <span class="payment-option-content" style="flex-direction:row;gap:6px;">
                                <span class="payment-option-icon">🏦</span>
                                <span class="payment-option-label" style="font-size:12px;">تحويل</span>
                            </span>
                        </label>
                        <label class="payment-option" style="flex:1;">
                            <input type="radio" name="buyPaymentMethod" value="فوري">
                            <span class="payment-option-content" style="flex-direction:row;gap:6px;">
                                <span class="payment-option-icon">💳</span>
                                <span class="payment-option-label" style="font-size:12px;">فوري</span>
                            </span>
                        </label>
                    </div>
                </div>
                <div class="buy-total-row">
                    الإجمالي: <span id="buyTotalPrice">${p.price}</span> ريال
                </div>
                <button class="checkout-btn" onclick="submitBuyOrder(${pid})" style="width:100%;margin-top:10px;">
                    ✅ تأكيد الطلب
                </button>
            </div>
        </div>`;
    
    content.dataset.productPrice = p.price;
    content.dataset.productName = p.name;
    buyCurrentQty = 1;
    
    openModal('buyModal');
}

function changeBuyQty(change) {
    const qtyEl = document.getElementById('buyQtyDisplay');
    const totalEl = document.getElementById('buyTotalPrice');
    const content = document.getElementById('buyModalContent');
    if (!qtyEl || !totalEl || !content) return;
    
    const newQty = buyCurrentQty + change;
    if (newQty < 1) return;
    
    buyCurrentQty = newQty;
    qtyEl.textContent = newQty;
    
    const price = parseFloat(content.dataset.productPrice) || 0;
    totalEl.textContent = (price * newQty).toFixed(0);
}

async function submitBuyOrder(pid) {
    const name = document.getElementById('buyName')?.value.trim();
    const phone = document.getElementById('buyPhone')?.value.trim();
    const address = document.getElementById('buyAddress')?.value.trim() || '';
    const qty = buyCurrentQty || 1;
    
    if (!name || !phone) { showAlert('يرجى إدخال الاسم والهاتف', 'error'); return; }
    
    const p = allProducts.find(x => x.id === pid);
    if (!p) { showAlert('المنتج غير موجود', 'error'); return; }
    
    // قراءة طريقة الدفع المحددة
    const paymentMethod = document.querySelector('input[name="buyPaymentMethod"]:checked')?.value || 'كاش';
    
    const items = [{ id: p.id, name: p.name, price: p.price, quantity: qty, size: p.size || 'قياسي', color: p.color || 'متنوع' }];
    const total = p.price * qty;
    
    try {
        const res = await fetch('/api/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_name: name, customer_phone: phone,
                customer_address: address, items: items, total_price: total,
                payment_method: paymentMethod
            })
        });
        const data = await res.json();
        if (res.ok) {
            let msg = `✅ تم تأكيد طلبك بنجاح! رقم الطلب: ${data.order_id}`;
            if (paymentMethod === 'تحويل بنكي') {
                msg += '\n🏦 بنكك: 123456789\n📸 أرسل صورة الإيداع على واتساب 249127599044';
            }
            showAlert(msg, 'success');
            closeModal('buyModal');
            buyCurrentQty = 1;
        } else showAlert(data.error, 'error');
    } catch (e) {
        showAlert('خطأ في الاتصال بالخادم', 'error');
    }
}

// ===== الشراء من الشات =====
function buyFromChat(pid) {
    const p = allProducts.find(x => x.id === pid);
    if (!p) { showAlert('المنتج غير موجود', 'error'); return; }
    if (p.stock <= 0) { showAlert('غير متوفر', 'error'); return; }
    
    // إضافة إلى السلة مباشرة
    const item = cart.find(x => x.id === pid);
    if (item) {
        if (item.quantity < p.stock) item.quantity++;
        else { showAlert('الكمية القصوى', 'warning'); return; }
    } else {
        cart.push({ id: p.id, name: p.name, price: p.price, quantity: 1, size: p.size || 'قياسي', color: p.color || 'متنوع' });
    }
    
    saveCart();
    updateCartCount();
    showAlert(`✅ تمت إضافة ${p.name} إلى السلة`, 'success');
    
    // عرض خيارات الدفع
    setTimeout(() => showPaymentOptions(), 500);
}

// ===== دوال مساعدة =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getCurrentTime() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
}

function scrollChatToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// حفظ السلة عند الإغلاق
window.addEventListener('beforeunload', saveCart);