import re

# ================= 1. آپدیت app.py (جداسازی داشبورد و قفل 24 ساعته) =================
with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1.1. تغییر مسیر داشبورد اصلی (فروشنده مستقیم بره POS)
dashboard_code = """
@app.route('/')
def dashboard():
    if not session.get('user_id'): return redirect(url_for('login'))
    
    # اگر فروشنده بود، مستقیم بره به فروش بصری
    if session.get('role') == 'seller':
        return redirect(url_for('pos'))
        
    conn = get_db()
    accounts = conn.execute("SELECT * FROM accounts").fetchall()
    
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    dead_stock = conn.execute(\"\"\"
        SELECT * FROM products 
        WHERE created_at < ? AND stock > 0 
        AND id NOT IN (SELECT product_id FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE type='sell' AND date > ?))
    \"\"\", (thirty_days_ago, thirty_days_ago)).fetchall()

    # آمار برای مدیر
    today = datetime.now().strftime('%Y-%m-%d')
    today_sales = conn.execute("SELECT SUM(total_amount) as total FROM invoices WHERE type='sell' AND date LIKE ?", (today+'%',)).fetchone()['total'] or 0
    
    conn.close()
    return render_template('dashboard.html', accounts=accounts, dead_stock=dead_stock, today_sales=today_sales)

@app.route('/reports')
def reports():
    if not session.get('user_id') or session.get('role') != 'admin': 
        return "شما دسترسی به این بخش ندارید!"
        
    conn = get_db()
    # گزارش فروش بر اساس کالا
    sales_by_product = conn.execute(\"\"\"
        SELECT p.name, SUM(ii.quantity) as qty, SUM(ii.quantity * ii.unit_price) as total
        FROM invoice_items ii
        JOIN products p ON ii.product_id = p.id
        JOIN invoices i ON ii.invoice_id = i.id
        WHERE i.type = 'sell'
        GROUP BY p.id ORDER BY qty DESC
    \"\"\").fetchall()
    conn.close()
    return render_template('reports.html', sales_by_product=sales_by_product)
"""
pattern_dash = r"@app\.route\('/'\)\s*def dashboard\(\):.*?(?=@app\.route\('/product/new'\)|\Z)"
code = re.sub(pattern_dash, dashboard_code, code, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

# ================= 2. آپدیت base.html (منوی متفاوت برای مدیر و فروشنده) =================
with open('templates/base.html', 'r', encoding='utf-8') as f:
    base = f.read()

# جایگزینی منوی پایین
new_nav = """
{% if session.get('user_id') %}
<div class="nav-bottom">
    {% if session.get('role') == 'admin' %}
        <a href="/" class="{% if request.path == '/' %}active{% endif %}"><span>🏠</span> داشبورد</a>
        <a href="/reports" class="{% if request.path == '/reports' %}active{% endif %}"><span>📊</span> گزارشات</a>
        <a href="/daybook" class="{% if request.path == '/daybook' %}active{% endif %}"><span>📒</span> حساب کتاب</a>
        <a href="/counterparties" class="{% if request.path == '/counterparties' %}active{% endif %}"><span>👥</span> طرف حساب</a>
    {% endif %}
    
    <a href="/pos" class="{% if request.path == '/pos' %}active{% endif %}"><span>🛒</span> فروش</a>
    <a href="/invoice/new/buy" class="{% if '/buy' in request.path %}active{% endif %}"><span>📦</span> خرید</a>
    <a href="/product/new" class="{% if request.path == '/product/new' %}active{% endif %}"><span>👕</span> کالا</a>
</div>
{% endif %}
"""
base = re.sub(r'<div class="nav-bottom">.*?</div>', new_nav, base, flags=re.DOTALL)
with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(base)

# ================= 3. ساخت صفحه گزارشات =================
reports_html = """{% extends 'base.html' %}{% block content %}
<div class="card"><div class="card-title">📊 گزارش فروش کالاها</div>
<table style="width:100%;text-align:right;font-size:14px">
<tr style="color:#00d4ff;border-bottom:1px solid #1a5276"><th>نام کالا</th><th>تعداد فروش</th><th>مبلغ کل</th></tr>
{% for item in sales_by_product %}
<tr style="border-bottom:1px dashed #1a5276">
<td style="padding:10px 0">{{ item.name }}</td>
<td style="color:#00ff88">{{ item.qty }}</td>
<td style="color:#ffd700">{{ "{:,}".format(item.total) }}</td>
</tr>
{% else %}
<tr><td colspan="3" style="text-align:center;padding:20px">هنوز فروشی ثبت نشده است.</td></tr>
{% endfor %}
</table>
</div>
{% endblock %}"""
with open('templates/reports.html', 'w', encoding='utf-8') as f:
    f.write(reports_html)

print("✅ نقش‌ها، منوها و صفحه گزارشات با موفقیت اصلاح شدند.")
