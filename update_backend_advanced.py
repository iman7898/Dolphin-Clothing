import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. آپدیت داشبورد (محاسبات سود، هزینه، نقطه سر به سر)
dashboard_code = """
@app.route('/')
def dashboard():
    if not session.get('user_id'): return redirect(url_for('login'))
    if session.get('role') == 'seller': return redirect(url_for('pos'))
        
    conn = get_db()
    accounts = conn.execute("SELECT * FROM accounts").fetchall()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # آمار فروش و خرید امروز
    sales_res = conn.execute("SELECT SUM(total_amount) as total FROM invoices WHERE type='sell' AND date LIKE ?", (today+'%',)).fetchone()
    buys_res = conn.execute("SELECT SUM(total_amount) as total FROM invoices WHERE type='buy' AND date LIKE ?", (today+'%',)).fetchone()
    expenses_res = conn.execute("SELECT SUM(amount) as total FROM expenses WHERE date LIKE ?", (today+'%',)).fetchone()
    
    today_sales = sales_res['total'] or 0
    today_buys = buys_res['total'] or 0
    today_expenses = expenses_res['total'] or 0
    
    # محاسبه سود امروز (فروش - (تعداد * قیمت خرید) - هزینه‌ها)
    cogs_res = conn.execute(\"\"\"
        SELECT SUM(ii.quantity * p.purchase_price) as cogs
        FROM invoice_items ii 
        JOIN products p ON ii.product_id = p.id 
        JOIN invoices i ON ii.invoice_id = i.id
        WHERE i.type = 'sell' AND i.date LIKE ?
    \"\"\", (today+'%',)).fetchone()
    
    cogs = cogs_res['cogs'] or 0
    today_profit = today_sales - cogs - today_expenses
    profit_percent = (today_profit / today_sales * 100) if today_sales > 0 else 0
    
    # نقطه سر به سر (کل هزینه‌ها / حاشیه سود)
    # برای سادگی: هزینه‌های امروز / (سود امروز / فروش امروز)
    bep = 0
    if today_sales > 0 and today_profit > 0:
        margin = today_profit / today_sales
        bep = today_expenses / margin if margin > 0 else 0

    # کالای راکد
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    dead_stock = conn.execute("SELECT * FROM products WHERE created_at < ? AND stock > 0 AND id NOT IN (SELECT product_id FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE type='sell' AND date > ?))", (thirty_days_ago, thirty_days_ago)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', accounts=accounts, dead_stock=dead_stock, 
                           today_sales=today_sales, today_buys=today_buys, today_expenses=today_expenses,
                           today_profit=today_profit, profit_percent=profit_percent, bep=bep)

@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if session.get('role') != 'admin': return "دسترسی غیرمجاز"
    conn = get_db()
    if request.method == 'POST':
        title = request.form['title']
        amount = int(request.form['amount'])
        conn.execute("INSERT INTO expenses (title, amount, date) VALUES (?, ?, ?)", (title, amount, datetime.now().strftime('%Y-%m-%d %H:%M')))
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = 1", (amount,))
        conn.commit()
        flash('هزینه ثبت شد', 'success')
    exps = conn.execute("SELECT * FROM expenses ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('expenses.html', expenses=exps)

# 2. API گرفتن اطلاعات کالا برای پنجره (Modal)
@app.route('/api/product_info/<int:id>')
def product_info(id):
    if not session.get('user_id'): return jsonify({'error': 'unauthorized'})
    conn = get_db()
    conn.row_factory = sqlite3.Row
    prod = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    
    if not prod:
        return jsonify({'error': 'not_found'})
        
    # آخرین خرید و فروش
    last_buy = conn.execute("SELECT ii.unit_price, i.date FROM invoice_items ii JOIN invoices i ON ii.invoice_id = i.id WHERE ii.product_id=? AND i.type='buy' ORDER BY i.id DESC LIMIT 1", (id,)).fetchone()
    last_sell = conn.execute("SELECT ii.unit_price, i.date FROM invoice_items ii JOIN invoices i ON ii.invoice_id = i.id WHERE ii.product_id=? AND i.type='sell' ORDER BY i.id DESC LIMIT 1", (id,)).fetchone()
    conn.close()
    
    return jsonify({
        'name': prod['name'],
        'stock': prod['stock'],
        'updated_at': prod['updated_at'] or 'ثبت نشده',
        'last_buy_price': last_buy['unit_price'] if last_buy else '---',
        'last_buy_date': last_buy['date'] if last_buy else '---',
        'last_sell_price': last_sell['unit_price'] if last_sell else '---',
        'last_sell_date': last_sell['date'] if last_sell else '---'
    })

"""
# جایگزینی داشبورد
pattern_dash = r"@app\.route\('/'\)\s*def dashboard\(\):.*?(?=@app\.route\('/product/new'\)|\Z)"
code = re.sub(pattern_dash, dashboard_code, code, flags=re.DOTALL)

# اضافه کردن ایمپورت jsonify
if 'jsonify' not in code:
    code = code.replace('from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file', 'from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify')

# اضافه کردن تاریخ ویرایش موقع ثبت کالا
code = code.replace("(barcode, name, sizes, colors, pur, sal, stock, datetime.now().strftime('%Y-%m-%d')))", "(barcode, name, sizes, colors, pur, sal, stock, datetime.now().strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d'))")
code = code.replace("INSERT INTO products (barcode, name, sizes, colors, purchase_price, sale_price, stock, created_at) VALUES (?,?,?,?,?,?,?,?)", "INSERT INTO products (barcode, name, sizes, colors, purchase_price, sale_price, stock, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("✅ بک‌اند (app.py) با موفقیت آپدیت شد.")
