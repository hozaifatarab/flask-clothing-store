// ===== المتغيرات العامة =====
let cart = JSON.parse(localStorage.getItem('cart')) || [];
let allProducts = [];
let currentCategory = 'all';

// ===== تهيئة الصفحة =====
document.addEventListener('DOMContentLoaded', function() {
    // تهيئة النافبار
    initNavbar();
    
    loadProducts();
    loadChat();
    updateCartCount();
    setInterval(loadChat, 3000); // تحديث الشات كل 3 ثوان
    
    // استرجاع حالة التصغير
    const isMinimized = localStorage.getItem('chatMinimized') === 'true';
    if (isMinimized) {
        minimizeChat();
    }
});

// ===== النافبار (القائمة المتنقلة) =====
function initNavbar() {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (!navToggle || !navMenu) return;
    
    navToggle.addEventListener('click', function() {
        navToggle.classList.toggle('active');
        navMenu.classList.toggle('active');
    });
    
    // إغلاق القائمة عند الضغط على رابط
    navMenu.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function() {
            navToggle.classList.remove('active');
            navMenu.classList.remove('active');
        });
    });
    
    // إغلاق القائمة عند الضغط خارجها
    document.addEventListener('click', function(e) {
        if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
            navToggle.classList.remove('active');
            navMenu.classList.remove('active');
        }
    });
}

// ===== تحميل المنتجات =====
async function loadProducts() {
    try {
        const response = await fetch('/api/products');
        const products = await response.json();
        allProducts = products;
        displayProducts(products);
    } catch (error) {
        console.error('Error loading products:', error);
        showAlert('خطأ في تحميل المنتجات', 'error');
    }
}

function displayProducts(products) {
    const productsGrid = document.getElementById('productsGrid');
    
    if (!productsGrid) return;
    
    if (products.length === 0) {
        productsGrid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="empty-state-icon">😞</div>
                <p>لا توجد منتجات في هذه الفئة</p>
            </div>
        `;
        return;
    }
    
    productsGrid.innerHTML = products.map(product => `
        <div class="product-card">
            <img src="${product.image || product.image_url}" alt="${product.name}" style="width:100%; height:200px; object-fit:cover; border-radius:15px;" onerror="this.src='https://via.placeholder.com/200?text=صورة'">
            <div class="product-info">
                <div class="product-name">${product.name}</div>
                <div class="product-description">${product.description || ''}</div>
                <div class="product-meta">
                    <span class="meta-item">الحجم: ${product.size || 'قياسي'}</span>
                    <span class="meta-item">اللون: ${product.color || 'متنوع'}</span>
                </div>
                <div class="product-price price">${product.price} ريال</div>
                <div class="product-stock">
                    ${product.stock > 0 
                        ? `✅ متوفر (${product.stock} بالمخزون)` 
                        : `❌ غير متوفر`}
                </div>
                <div class="product-buttons">
                    <button class="btn-details" onclick="viewProductDetails(${product.id})">📋 التفاصيل</button>
                    <button class="btn-add" onclick="addToCart(${product.id})" 
                            ${product.stock <= 0 ? 'disabled' : ''}>
                        🛒 أضف للسلة
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// ===== البحث والتصفية =====
function searchProducts() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    const filtered = allProducts.filter(product => 
        product.name.toLowerCase().includes(searchTerm) ||
        (product.description || '').toLowerCase().includes(searchTerm)
    );
    
    displayProducts(filtered);
}

function filterByCategory(category) {
    currentCategory = category;
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.value = '';
    
    if (category === 'all') {
        displayProducts(allProducts);
    } else {
        const filtered = allProducts.filter(p => p.category === category);
        displayProducts(filtered);
    }
}

// ===== تفاصيل المنتج =====
async function viewProductDetails(productId) {
    try {
        const response = await fetch(`/api/product/${productId}`);
        const product = await response.json();
        
        const modal = document.getElementById('productModal');
        const detailDiv = document.getElementById('productDetail');
        
        if (!modal || !detailDiv) return;
        
        detailDiv.innerHTML = `
            <div class="product-detail">
                <div class="product-detail-image">
                    <img src="${product.image || product.image_url}" alt="${product.name}" style="width:100%;height:100%;object-fit:cover;" onerror="this.src='https://via.placeholder.com/400?text=صورة+المنتج'">
                </div>
                <div class="product-detail-info">
                    <h2>${product.name}</h2>
                    <div class="detail-rating">⭐⭐⭐⭐⭐ (4.8/5 - 245 تقييم)</div>
                    <div class="detail-price">${product.price} ريال</div>
                    <div class="detail-description">${product.description || ''}</div>
                    
                    <div class="detail-specs">
                        <div class="spec-item">
                            <span>الفئة:</span>
                            <strong>${product.category === 'رجالي' ? '👔 رجالي' : product.category === 'نسائي' ? '👗 نسائي' : product.category}</strong>
                        </div>
                        <div class="spec-item">
                            <span>الحجم:</span>
                            <strong>${product.size || 'قياسي'}</strong>
                        </div>
                        <div class="spec-item">
                            <span>اللون:</span>
                            <strong>${product.color || 'متنوع'}</strong>
                        </div>
                        <div class="spec-item">
                            <span>المخزون:</span>
                            <strong>${product.stock} قطعة</strong>
                        </div>
                        <div class="spec-item">
                            <span>الحالة:</span>
                            <strong>${product.stock > 0 ? '✅ متوفر الآن' : '❌ غير متوفر حالياً'}</strong>
                        </div>
                    </div>
                    
                    <div class="detail-buttons">
                        <button class="btn-add-cart" onclick="addToCart(${product.id}); closeProductModal();"
                                ${product.stock <= 0 ? 'disabled' : ''}>
                            🛒 أضف للسلة
                        </button>
                        <button class="btn-wishlist" onclick="addToWishlist(${product.id})">
                            ❤️ أضف للمفضلة
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        modal.classList.add('active');
    } catch (error) {
        console.error('Error loading product details:', error);
        showAlert('خطأ في تحميل تفاصيل المنتج', 'error');
    }
}

function closeProductModal() {
    const modal = document.getElementById('productModal');
    if (modal) modal.classList.remove('active');
}

// ===== سلة التسوق =====
function addToCart(productId) {
    const product = allProducts.find(p => p.id === productId);
    
    if (!product) {
        showAlert('المنتج غير موجود', 'error');
        return;
    }
    
    if (product.stock <= 0) {
        showAlert('المنتج غير متوفر في المخزون', 'error');
        return;
    }
    
    // البحث عن المنتج في السلة
    const cartItem = cart.find(item => item.id === productId);
    
    if (cartItem) {
        if (cartItem.quantity < product.stock) {
            cartItem.quantity++;
        } else {
            showAlert('لا يمكن إضافة أكثر من المتوفر', 'warning');
            return;
        }
    } else {
        cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            color: product.color || 'متنوع',
            size: product.size || 'قياسي',
            quantity: 1
        });
    }
    
    saveCart();
    updateCartCount();
    showAlert(`✅ تمت إضافة ${product.name} إلى السلة`, 'success');
}

function saveCart() {
    localStorage.setItem('cart', JSON.stringify(cart));
}

function updateCartCount() {
    const count = cart.reduce((total, item) => total + item.quantity, 0);
    const badge = document.getElementById('cartBadge') || document.getElementById('cart-count');
    if (badge) {
        badge.textContent = count;
    }
}

function openCart() {
    displayCart();
    const modal = document.getElementById('cartModal');
    if (modal) modal.classList.add('active');
}

function closeCart() {
    const modal = document.getElementById('cartModal');
    if (modal) modal.classList.remove('active');
}

function displayCart() {
    const cartItemsDiv = document.getElementById('cartItems');
    
    if (!cartItemsDiv) return;
    
    if (cart.length === 0) {
        cartItemsDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🛒</div>
                <p>السلة فارغة</p>
            </div>
        `;
        const checkoutSection = document.getElementById('checkoutSection');
        if (checkoutSection) checkoutSection.style.display = 'none';
        return;
    }
    
    const checkoutSection = document.getElementById('checkoutSection');
    if (checkoutSection) checkoutSection.style.display = 'block';
    
    cartItemsDiv.innerHTML = cart.map((item, index) => `
        <div class="cart-item">
            <div class="cart-item-info">
                <div class="cart-item-name">${item.name}</div>
                <div class="cart-item-details">
                    الحجم: ${item.size} | اللون: ${item.color}
                </div>
                <div class="cart-item-price">${item.price} ريال</div>
            </div>
            <div class="cart-item-quantity">
                <button class="qty-btn" onclick="updateQuantity(${index}, -1)">−</button>
                <span style="min-width: 30px; text-align: center;">${item.quantity}</span>
                <button class="qty-btn" onclick="updateQuantity(${index}, 1)">+</button>
            </div>
            <button class="remove-btn" onclick="removeFromCart(${index})">حذف</button>
        </div>
    `).join('');
    
    updateCartTotal();
}

function updateQuantity(index, change) {
    const product = allProducts.find(p => p.id === cart[index].id);
    
    if (!product) return;
    
    if (cart[index].quantity + change > 0 && cart[index].quantity + change <= product.stock) {
        cart[index].quantity += change;
        saveCart();
        updateCartCount();
        displayCart();
    }
}

function removeFromCart(index) {
    if (confirm('هل تريد حذف هذا المنتج من السلة؟')) {
        cart.splice(index, 1);
        saveCart();
        updateCartCount();
        displayCart();
    }
}

function updateCartTotal() {
    const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const cartTotal = document.getElementById('cartTotal');
    const subtotal = document.getElementById('subtotal');
    const itemCount = document.getElementById('itemCount');
    
    if (cartTotal) cartTotal.textContent = total.toFixed(2);
    if (subtotal) subtotal.textContent = total.toFixed(2) + ' ريال';
    if (itemCount) itemCount.textContent = cart.reduce((sum, item) => sum + item.quantity, 0);
}

async function checkoutCart() {
    const name = document.getElementById('customerName').value.trim();
    const phone = document.getElementById('customerPhone').value.trim();
    const email = document.getElementById('customerEmail');
    const emailValue = email ? email.value.trim() : '';
    
    if (!name || !phone) {
        showAlert('يرجى إدخال الاسم ورقم الهاتف', 'error');
        return;
    }
    
    if (cart.length === 0) {
        showAlert('السلة فارغة', 'error');
        return;
    }
    
    const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
    try {
        const response = await fetch('/api/orders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                customer_name: name,
                customer_phone: phone,
                customer_address: emailValue,
                items: cart,
                total_price: total
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            cart = [];
            saveCart();
            updateCartCount();
            closeCart();
            if (document.getElementById('customerName')) document.getElementById('customerName').value = '';
            if (document.getElementById('customerPhone')) document.getElementById('customerPhone').value = '';
            if (email) email.value = '';
        } else {
            showAlert(result.error, 'error');
        }
    } catch (error) {
        console.error('Error creating order:', error);
        showAlert('خطأ في معالجة الطلب', 'error');
    }
}

function addToWishlist(productId) {
    showAlert('✅ تمت إضافة المنتج للمفضلة', 'success');
}

// ===== دوال التكبير والتصغير =====
function minimizeChat() {
    const chatPanel = document.getElementById('chatPanel');
    const chatButton = document.getElementById('chat-button');
    const minimizedIcon = document.getElementById('chatMinimizedIcon');
    
    if (!chatPanel) return;
    
    // إخفاء الشات وإظهار الأيقونة المصغرة
    chatPanel.classList.remove('active');
    chatPanel.classList.remove('maximized');
    if (chatButton) chatButton.style.display = 'none';
    if (minimizedIcon) minimizedIcon.style.display = 'flex';
    
    // حفظ الحالة
    localStorage.setItem('chatMinimized', 'true');
}

function maximizeChat() {
    const chatPanel = document.getElementById('chatPanel');
    const chatButton = document.getElementById('chat-button');
    const minimizedIcon = document.getElementById('chatMinimizedIcon');
    
    if (!chatPanel) return;
    
    // إظهار الشات بحجم كبير
    chatPanel.classList.add('active');
    chatPanel.classList.add('maximized');
    if (chatButton) chatButton.style.display = 'none';
    if (minimizedIcon) minimizedIcon.style.display = 'none';
    
    // حفظ الحالة
    localStorage.setItem('chatMinimized', 'false');
    
    // التمرير للأسفل
    setTimeout(() => {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 200);
}

function restoreChat() {
    const chatPanel = document.getElementById('chatPanel');
    const chatButton = document.getElementById('chat-button');
    const minimizedIcon = document.getElementById('chatMinimizedIcon');
    
    if (!chatPanel) return;
    
    // إظهار الشات بحجم عادي
    chatPanel.classList.add('active');
    chatPanel.classList.remove('maximized');
    if (chatButton) chatButton.style.display = 'none';
    if (minimizedIcon) minimizedIcon.style.display = 'none';
    
    // حفظ الحالة
    localStorage.setItem('chatMinimized', 'false');
    
    // إرسال التحية التلقائية إذا لزم الأمر
    if (!chatInitialized) {
        chatInitialized = true;
        sendAutoGreeting();
    }
    
    // التمرير للأسفل
    setTimeout(() => {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 200);
}

// ===== دوال الخروج ومسح الشات =====
function closeChatWithPrompt() {
    const modal = document.getElementById('exitChatModal');
    if (modal) modal.classList.add('active');
}

function cancelExitChat() {
    const modal = document.getElementById('exitChatModal');
    if (modal) modal.classList.remove('active');
}

async function downloadChatAsPDF() {
    try {
        // جلب الرسائل
        const response = await fetch('/api/messages');
        const messages = await response.json();
        
        if (messages.length === 0) {
            showAlert('لا توجد رسائل لتحميلها', 'warning');
            return;
        }
        
        // بناء HTML للمحادثة
        const now = new Date();
        const dateStr = now.toLocaleDateString('ar-SA', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        let chatHtml = `
            <div style="direction:rtl; font-family: 'Cairo', Arial, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
                <div style="text-align:center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #6a11cb;">
                    <h1 style="color:#6a11cb; font-size:22px; margin:0;">💬 محادثة متجر الملابس</h1>
                    <p style="color:#888; font-size:13px; margin:5px 0 0 0;">تاريخ التحميل: ${dateStr}</p>
                </div>
                <div style="margin-bottom: 15px;">
        `;
        
        messages.forEach(msg => {
            const isAdmin = msg.sender === 'كارم';
            const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('ar-SA', { 
                hour: '2-digit', 
                minute: '2-digit' 
            }) : '';
            
            chatHtml += `
                <div style="margin-bottom: 12px; text-align: ${isAdmin ? 'right' : 'left'};">
                    <div style="display:inline-block; max-width:80%; padding:10px 14px; border-radius:12px; 
                        ${isAdmin 
                            ? 'background:linear-gradient(90deg, #6a11cb, #2575fc); color:white; border-bottom-left-radius:0;' 
                            : 'background:#f0f0f0; color:#333; border-bottom-right-radius:0;'
                        }">
                        <div style="font-size:13px; line-height:1.5;">${msg.message}</div>
                        <div style="font-size:10px; margin-top:4px; opacity:0.7;">${time}</div>
                    </div>
                </div>
            `;
        });
        
        chatHtml += `
                </div>
                <div style="text-align:center; margin-top:20px; padding-top:15px; border-top:1px solid #ddd; color:#888; font-size:11px;">
                    <p>تم إنشاء هذا الملف بواسطة متجر الملابس</p>
                    <p>جميع الحقوق محفوظة &copy; 2026</p>
                </div>
            </div>
        `;
        
        // إخفاء المودال أولاً
        const exitModal = document.getElementById('exitChatModal');
        if (exitModal) exitModal.classList.remove('active');
        
        // تحويل إلى PDF باستخدام html2pdf
        const element = document.createElement('div');
        element.innerHTML = chatHtml;
        element.style.position = 'absolute';
        element.style.left = '-9999px';
        element.style.top = '0';
        document.body.appendChild(element);
        
        const opt = {
            margin:       10,
            filename:     `chat_${now.getTime()}.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2, useCORS: true },
            jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
        };
        
        await html2pdf().set(opt).from(element).save();
        
        // إزالة العنصر المؤقت
        document.body.removeChild(element);
        
        showAlert('✅ تم تحميل المحادثة بنجاح', 'success');
        
        // مسح الشات بعد التحميل
        await clearMessages();
        
    } catch (error) {
        console.error('Error downloading PDF:', error);
        showAlert('خطأ في تحميل المحادثة', 'error');
    }
}

async function clearChatAndExit() {
    // إخفاء المودال
    const exitModal = document.getElementById('exitChatModal');
    if (exitModal) exitModal.classList.remove('active');
    
    // مسح الرسائل
    await clearMessages();
    
    showAlert('🗑️ تم مسح المحادثة', 'info');
}

async function clearMessages() {
    try {
        await fetch('/api/messages', {
            method: 'DELETE'
        });
        
        // إعادة تعيين المتغيرات
        chatInitialized = false;
        
        // إخفاء الشات
        const chatPanel = document.getElementById('chatPanel');
        if (chatPanel) chatPanel.classList.remove('active');
        if (chatPanel) chatPanel.classList.remove('maximized');
        const chatButton = document.getElementById('chat-button');
        if (chatButton) chatButton.style.display = 'flex';
        const minimizedIcon = document.getElementById('chatMinimizedIcon');
        if (minimizedIcon) minimizedIcon.style.display = 'none';
        
        // إلغاء حفظ حالة التصغير
        localStorage.setItem('chatMinimized', 'false');
        
        // تحديث الشات
        loadChat();
    } catch (error) {
        console.error('Error clearing messages:', error);
        showAlert('خطأ في مسح المحادثة', 'error');
    }
}

// ===== نظام الشات =====
let chatInitialized = false;

async function loadChat() {
    try {
        const response = await fetch('/api/messages');
        const messages = await response.json();
        displayChat(messages);
        
        // إذا الشات فاتح ولسه ما انرسلت التحية, نرسل ترحيب تلقائي
        const chatPanel = document.getElementById('chatPanel');
        if (chatPanel && chatPanel.classList.contains('active') && !chatInitialized) {
            chatInitialized = true;
            // نتحقق إذا في رسايل أصلاً
            const hasMessages = messages.length > 0;
            if (!hasMessages) {
                await sendAutoGreeting();
            }
        }
    } catch (error) {
        console.error('Error loading chat:', error);
    }
}

async function sendAutoGreeting() {
    try {
        // إرسال رسالة ترحيب من كارم تلقائياً
        const aiResponse = await fetch('/api/smart-response', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: 'سلام'
            })
        });
        
        if (aiResponse.ok) {
            const data = await aiResponse.json();
            
            let adminMessage = data.reply;
            if (data.html_cards) {
                adminMessage += data.html_cards;
            }
            
            await fetch('/api/messages/admin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: adminMessage,
                    session_id: 'default'
                })
            });
            
            loadChat();
        }
    } catch (error) {
        console.error('Error sending auto greeting:', error);
    }
}

function displayChat(messages) {
    const chatDiv = document.getElementById('chatMessages');
    
    if (!chatDiv) return;
    
    if (messages.length === 0) {
        chatDiv.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #999;">
                <p>لا توجد رسائل حتى الآن</p>
                <p style="font-size: 12px;">ابدأ المحادثة مع البائع</p>
            </div>
        `;
        return;
    }
    
    chatDiv.innerHTML = messages.map(msg => {
        // التحقق إذا كانت الرسالة تحتوي على HTML كروت منتجات
        const isAdmin = msg.sender === 'كارم';
        const messageContent = msg.message;
        
        return `
            <div class="message ${isAdmin ? 'message-admin' : 'message-user'}">
                <div class="message-bubble">
                    ${messageContent}
                    <div class="message-time">
                        ${msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('ar-SA', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        }) : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // التمرير للأسفل تلقائياً
    chatDiv.scrollTop = chatDiv.scrollHeight;
}

async function toggleChat() {
    const chatPanel = document.getElementById('chatPanel');
    const chatButton = document.getElementById('chat-button');
    const minimizedIcon = document.getElementById('chatMinimizedIcon');
    
    if (!chatPanel) return;
    
    // إذا كان الشات مصغر، نرجعه
    if (minimizedIcon && minimizedIcon.style.display === 'flex') {
        restoreChat();
        return;
    }
    
    chatPanel.classList.toggle('active');
    
    if (chatPanel.classList.contains('active')) {
        if (chatButton) chatButton.style.display = 'none';
        if (minimizedIcon) minimizedIcon.style.display = 'none';
        
        // نرسل التحية التلقائية أول ما العميل يفتح الشات
        if (!chatInitialized) {
            chatInitialized = true;
            await sendAutoGreeting();
        }
        setTimeout(() => {
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 200);
    } else {
        if (chatButton) chatButton.style.display = 'flex';
    }
}

function handleChatKeypress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const senderName = 'زبون';
    const messageText = document.getElementById('messageInput').value.trim();
    
    if (!messageText) {
        showAlert('يرجى إدخال الرسالة', 'warning');
        return;
    }
    
    try {
        // إرسال رسالة المستخدم
        const response = await fetch('/api/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sender: senderName,
                message: messageText,
                session_id: 'default'
            })
        });
        
        if (response.ok) {
            const messageInput = document.getElementById('messageInput');
            if (messageInput) messageInput.value = '';
            
            // الحصول على رد ذكي من الشات
            try {
                const aiResponse = await fetch('/api/smart-response', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: messageText
                    })
                });
                
                if (aiResponse.ok) {
                    const data = await aiResponse.json();
                    
                    // بناء رسالة الرد - إذا كان فيه html_cards نضيفها
                    let adminMessage = data.reply;
                    if (data.html_cards) {
                        adminMessage += data.html_cards;
                    }
                    
                    // إرسال رد الشات الذكي تلقائياً
                    await fetch('/api/messages/admin', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            message: adminMessage,
                            session_id: 'default'
                        })
                    });
                }
            } catch (error) {
                console.error('Error getting AI response:', error);
            }
            
            // تحديث الشات
            loadChat();
        } else {
            showAlert('خطأ في إرسال الرسالة', 'error');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        showAlert('خطأ في الاتصال', 'error');
    }
}

// ===== عرض تفاصيل المنتج مع الدفع في الشات =====
async function showProductDetailInChat(productId) {
    try {
        const response = await fetch(`/api/chat/product-detail/${productId}`);
        if (!response.ok) {
            showAlert('خطأ في تحميل تفاصيل المنتج', 'error');
            return;
        }
        
        const data = await response.json();
        
        // بناء رسالة الرد كاملة
        let adminMessage = data.reply;
        if (data.html_cards) {
            adminMessage += data.html_cards;
        }
        
        // إرسال رسالة كارم بالتفاصيل وطريقة الدفع
        await fetch('/api/messages/admin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: adminMessage,
                session_id: 'default'
            })
        });
        
        // تحديث الشات
        loadChat();
    } catch (error) {
        console.error('Error showing product detail in chat:', error);
        showAlert('خطأ في تحميل تفاصيل المنتج', 'error');
    }
}

// ===== الرسائل والتنبيهات =====
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    alertDiv.style.maxWidth = '500px';
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.animation = 'slideUp 0.3s ease reverse';
        setTimeout(() => alertDiv.remove(), 300);
    }, 3000);
}

// ===== تأثيرات إضافية =====
document.addEventListener('click', function(event) {
    if (event.target.id === 'cartModal') {
        closeCart();
    }
    if (event.target.id === 'productModal') {
        closeProductModal();
    }
    if (event.target.id === 'exitChatModal') {
        cancelExitChat();
    }
});

// تحديث الصفحة عند إغلاق لسان التطبيق
window.addEventListener('beforeunload', function() {
    saveCart();
});