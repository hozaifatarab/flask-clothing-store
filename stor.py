"""
تطبيق متجر ملابس احترافي
Clothing Store Application
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import json

class ClothingStore:
    def __init__(self, root):
        self.root = root
        self.root.title("متجر الملابس - Clothing Store")
        self.root.geometry("1000x650")
        self.root.config(bg="#f0f0f0")
        
        # تهيئة قاعدة البيانات
        self.init_database()
        
        # المتغيرات
        self.current_user = None
        self.cart = []
        
        # عرض شاشة تسجيل الدخول
        self.show_login_screen()
    
    def init_database(self):
        """تهيئة قاعدة البيانات"""
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # جدول المنتجات
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                size TEXT NOT NULL,
                color TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL,
                image_path TEXT
            )
        ''')
        
        # جدول المستخدمين
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT
            )
        ''')
        
        # جدول الطلبات
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                order_date TEXT,
                total REAL,
                status TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # جدول تفاصيل الطلبات
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                price REAL,
                FOREIGN KEY(order_id) REFERENCES orders(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        ''')
        
        self.conn.commit()
        self.add_sample_products()
    
    def add_sample_products(self):
        """إضافة عينات من المنتجات"""
        products = [
            ("قميص رجالي أزرق", "رجالي", "M", "أزرق", 150, 20),
            ("قميص رجالي أسود", "رجالي", "L", "أسود", 150, 15),
            ("فستان نسائي أحمر", "نسائي", "M", "أحمر", 300, 10),
            ("فستان نسائي أسود", "نسائي", "L", "أسود", 280, 8),
            ("بنطال رجالي", "رجالي", "32", "أسود", 200, 25),
            ("بنطال نسائي", "نسائي", "28", "أزرق", 220, 18),
            ("جاكيت جلدي", "رجالي", "M", "بني", 500, 5),
            ("معطف نسائي", "نسائي", "M", "رمادي", 450, 7),
        ]
        
        for product in products:
            self.cursor.execute('''
                INSERT OR IGNORE INTO products (name, category, size, color, price, stock)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', product)
        
        self.conn.commit()
    
    def clear_window(self):
        """مسح جميع العناصر من النافذة"""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show_login_screen(self):
        """عرض شاشة تسجيل الدخول"""
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ttk.Label(frame, text="متجر الملابس", font=("Arial", 24, "bold")).pack(pady=20)
        
        ttk.Label(frame, text="اسم المستخدم:", font=("Arial", 12)).pack(pady=5)
        username_entry = ttk.Entry(frame, width=30)
        username_entry.pack(pady=5)
        
        ttk.Label(frame, text="كلمة المرور:", font=("Arial", 12)).pack(pady=5)
        password_entry = ttk.Entry(frame, width=30, show="*")
        password_entry.pack(pady=5)
        
        def login():
            username = username_entry.get()
            password = password_entry.get()
            
            if not username or not password:
                messagebox.showerror("خطأ", "الرجاء إدخال اسم المستخدم وكلمة المرور")
                return
            
            # التحقق من المستخدم
            self.cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                              (username, password))
            user = self.cursor.fetchone()
            
            if user:
                self.current_user = username
                self.show_main_screen()
            else:
                messagebox.showerror("خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة")
        
        def register():
            username = username_entry.get()
            password = password_entry.get()
            
            if not username or not password:
                messagebox.showerror("خطأ", "الرجاء إدخال اسم المستخدم وكلمة المرور")
                return
            
            try:
                self.cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                                  (username, password))
                self.conn.commit()
                messagebox.showinfo("نجاح", "تم إنشاء حساب جديد بنجاح!")
                self.current_user = username
                self.show_main_screen()
            except sqlite3.IntegrityError:
                messagebox.showerror("خطأ", "اسم المستخدم موجود بالفعل")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="دخول", command=login).pack(side="left", padx=5)
        ttk.Button(button_frame, text="إنشاء حساب", command=register).pack(side="left", padx=5)
    
    def show_main_screen(self):
        """عرض الشاشة الرئيسية"""
        self.clear_window()
        self.cart = []
        
        # الشريط العلوي
        top_bar = ttk.Frame(self.root)
        top_bar.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(top_bar, text=f"أهلاً {self.current_user}", font=("Arial", 14, "bold")).pack(side="left")
        ttk.Button(top_bar, text="تسجيل الخروج", command=self.show_login_screen).pack(side="right", padx=5)
        ttk.Button(top_bar, text="سلة التسوق", command=self.show_cart).pack(side="right", padx=5)
        
        # القسم الرئيسي
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # شريط البحث والتصفية
        search_frame = ttk.LabelFrame(main_frame, text="البحث والتصفية", padding="10")
        search_frame.pack(fill="x", pady=10)
        
        ttk.Label(search_frame, text="البحث:").pack(side="left", padx=5)
        search_entry = ttk.Entry(search_frame, width=20)
        search_entry.pack(side="left", padx=5)
        
        ttk.Label(search_frame, text="الفئة:").pack(side="left", padx=5)
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(search_frame, textvariable=category_var, 
                                      values=["الكل", "رجالي", "نسائي"], state="readonly", width=15)
        category_combo.set("الكل")
        category_combo.pack(side="left", padx=5)
        
        # إطار المنتجات
        products_frame = ttk.LabelFrame(main_frame, text="المنتجات", padding="10")
        products_frame.pack(fill="both", expand=True, pady=10)
        
        # Treeview للمنتجات
        columns = ("ID", "الاسم", "الفئة", "الحجم", "اللون", "السعر", "المخزون")
        tree = ttk.Treeview(products_frame, columns=columns, height=15)
        
        tree.column("#0", width=0, stretch="no")
        tree.column("ID", width=30)
        tree.column("الاسم", width=150)
        tree.column("الفئة", width=80)
        tree.column("الحجم", width=60)
        tree.column("اللون", width=80)
        tree.column("السعر", width=80)
        tree.column("المخزون", width=80)
        
        tree.heading("#0", text="")
        tree.heading("ID", text="ID")
        tree.heading("الاسم", text="الاسم")
        tree.heading("الفئة", text="الفئة")
        tree.heading("الحجم", text="الحجم")
        tree.heading("اللون", text="اللون")
        tree.heading("السعر", text="السعر")
        tree.heading("المخزون", text="المخزون")
        
        tree.pack(fill="both", expand=True)
        
        def load_products():
            for item in tree.get_children():
                tree.delete(item)
            
            search_text = search_entry.get()
            category = category_var.get()
            
            if category == "الكل":
                query = "SELECT * FROM products WHERE name LIKE ?"
                self.cursor.execute(query, (f"%{search_text}%",))
            else:
                query = "SELECT * FROM products WHERE name LIKE ? AND category = ?"
                self.cursor.execute(query, (f"%{search_text}%", category))
            
            products = self.cursor.fetchall()
            for product in products:
                tree.insert("", "end", values=product)
        
        def add_to_cart():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("تحذير", "الرجاء اختيار منتج")
                return
            
            item = tree.item(selection[0])
            product_id = item['values'][0]
            
            quantity_window = tk.Toplevel(self.root)
            quantity_window.title("إضافة إلى السلة")
            quantity_window.geometry("300x150")
            
            ttk.Label(quantity_window, text="الكمية:", font=("Arial", 12)).pack(pady=10)
            quantity_entry = ttk.Entry(quantity_window, width=10)
            quantity_entry.pack(pady=10)
            quantity_entry.insert(0, "1")
            
            def confirm_add():
                try:
                    quantity = int(quantity_entry.get())
                    self.cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
                    product = self.cursor.fetchone()
                    
                    if quantity > product[6]:  # التحقق من المخزون
                        messagebox.showerror("خطأ", "الكمية المطلوبة غير متوفرة في المخزون")
                        return
                    
                    self.cart.append((product, quantity))
                    messagebox.showinfo("نجاح", "تمت إضافة المنتج إلى السلة")
                    quantity_window.destroy()
                except ValueError:
                    messagebox.showerror("خطأ", "الرجاء إدخال كمية صحيحة")
            
            ttk.Button(quantity_window, text="تأكيد", command=confirm_add).pack(pady=10)
        
        # أزرار التحكم
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)
        
        ttk.Button(control_frame, text="بحث", command=load_products).pack(side="left", padx=5)
        ttk.Button(control_frame, text="إضافة إلى السلة", command=add_to_cart).pack(side="left", padx=5)
        ttk.Button(control_frame, text="تحديث", command=load_products).pack(side="left", padx=5)
        
        # تحميل المنتجات في البداية
        load_products()
    
    def show_cart(self):
        """عرض سلة التسوق"""
        self.clear_window()
        
        # الشريط العلوي
        top_bar = ttk.Frame(self.root)
        top_bar.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(top_bar, text="العودة", command=self.show_main_screen).pack(side="left", padx=5)
        ttk.Label(top_bar, text="سلة التسوق", font=("Arial", 14, "bold")).pack(side="left", expand=True)
        
        # محتويات السلة
        if not self.cart:
            ttk.Label(self.root, text="السلة فارغة", font=("Arial", 14)).pack(pady=50)
            return
        
        cart_frame = ttk.LabelFrame(self.root, text="المنتجات في السلة", padding="10")
        cart_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # الجدول
        columns = ("الاسم", "السعر", "الكمية", "الإجمالي")
        tree = ttk.Treeview(cart_frame, columns=columns, height=15)
        
        tree.column("#0", width=0, stretch="no")
        tree.column("الاسم", width=200)
        tree.column("السعر", width=100)
        tree.column("الكمية", width=100)
        tree.column("الإجمالي", width=150)
        
        tree.heading("#0", text="")
        tree.heading("الاسم", text="الاسم")
        tree.heading("السعر", text="السعر")
        tree.heading("الكمية", text="الكمية")
        tree.heading("الإجمالي", text="الإجمالي")
        
        total = 0
        for product, quantity in self.cart:
            item_total = product[5] * quantity
            total += item_total
            tree.insert("", "end", values=(product[1], product[5], quantity, item_total))
        
        tree.pack(fill="both", expand=True)
        
        # ملخص الطلب
        summary_frame = ttk.Frame(self.root)
        summary_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(summary_frame, text=f"الإجمالي: {total} ريال", font=("Arial", 14, "bold")).pack(pady=10)
        
        def checkout():
            if messagebox.askyesno("تأكيد", f"هل تريد إتمام الشراء؟\nالإجمالي: {total} ريال"):
                # إنشاء الطلب
                self.cursor.execute('SELECT id FROM users WHERE username = ?', (self.current_user,))
                user_id = self.cursor.fetchone()[0]
                
                self.cursor.execute('''
                    INSERT INTO orders (user_id, order_date, total, status)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total, "pending"))
                
                order_id = self.cursor.lastrowid
                
                for product, quantity in self.cart:
                    self.cursor.execute('''
                        INSERT INTO order_items (order_id, product_id, quantity, price)
                        VALUES (?, ?, ?, ?)
                    ''', (order_id, product[0], quantity, product[5]))
                
                self.conn.commit()
                messagebox.showinfo("نجاح", "تم الطلب بنجاح!\nشكراً لتسوقك معنا")
                self.show_main_screen()
        
        button_frame = ttk.Frame(summary_frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="إتمام الشراء", command=checkout).pack(side="left", padx=5)


def main():
    root = tk.Tk()
    app = ClothingStore(root)
    root.mainloop()


if __name__ == "__main__":
    main()
