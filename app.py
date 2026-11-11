from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import sqlite3
import libsql
import os
from dotenv import load_dotenv
load_dotenv(), os, qrcode, io
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'dolphin_secret'

def get_db():
    conn = libsql.connect(
        database="local.db",
        sync_url=os.getenv("TURSO_DATABASE_URL"),
        auth_token=os.getenv("TURSO_AUTH_TOKEN"),
        sync_interval=60
    )
    conn.sync()
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        password = request.form.get('password')
        
        if role == 'admin' and password == 'iman7898':
            session['user_id'] = 1
            session['role'] = 'admin'
            return redirect(url_for('dashboard'))
        elif role == 'seller' and password == 'shok12':
            session['user_id'] = 2
            session['role'] = 'seller'
            return redirect(url_for('dashboard'))
        else:
            flash('❌ رمز عبور اشتباه است!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    if not session.get('user_id'): return redirect(url_for('login'))
    if session.get('role') == 'seller': return redirect(url_for('pos'))
        
    conn = get_db()
    accounts = conn.execute("SELECT * FROM accounts").fetchall()
    today = datetime.now().strftime('%Y-%m-%d')
    
    today_sales = conn.execute("SELECT SUM(total_amount) as total FROM invoices WHERE type='sell' AND date LIKE ?", (today+'%',)).fetchone()['total'] or 0
    today_buys = conn.execute("SELECT SUM(total_amount) as total FROM invoices WHERE type='buy' AND date LIKE ?", (today+'%',)).fetchone()['total'] or 0
    today_expenses = conn.execute("SELECT SUM(amount) as total FROM expenses WHERE date LIKE ?", (today+'%',)).fetchone()['total'] or 0
    
    cogs_query = """
        SELECT SUM(ii.quantity * p.purchase_price) as cogs
        FROM invoice_items ii 
        JOIN products p ON ii.product_id = p.id 
        JOIN invoices i ON ii.invoice_id = i.id
        WHERE i.type = 'sell' AND i.date LIKE ?
    """
    cogs = conn.execute(cogs_query, (today+'%',)).fetchone()['cogs'] or 0
    today_profit = today_sales - cogs - today_expenses
    profit_percent = (today_profit / today_sales * 100) if today_sales > 0 else 0
    
    bep = 0
    if today_sales > 0 and today_profit > 0:
        margin = today_profit / today_sales
        bep = today_expenses / margin if margin > 0 else 0

    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    dead_stock = conn.execute("SELECT * FROM products WHERE created_at < ? AND stock > 0 AND id NOT IN (SELECT product_id FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE type='sell' AND date > ?))", (thirty_days_ago, thirty_days_ago)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', accounts=accounts, dead_stock=dead_stock, 
                           today_sales=today_sales, today_buys=today_buys, today_expenses=today_expenses,
                           today_profit=today_profit, profit_percent=profit_percent, bep=bep)

@app.route('/reports')
def reports():
    if session.get('role') != 'admin': return "دسترسی غیرمجاز"
    conn = get_db()
    sales = conn.execute("SELECT p.name, SUM(ii.quantity) as qty, SUM(ii.quantity * ii.unit_price) as total FROM invoice_items ii JOIN products p ON ii.product_id = p.id JOIN invoices i ON ii.invoice_id = i.id WHERE i.type = 'sell' GROUP BY p.id ORDER BY qty DESC").fetchall()
    conn.close()
    return render_template('reports.html', sales=sales)

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

@app.route('/api/product_info/<int:id>')
def product_info(id):
    if not session.get('user_id'): return jsonify({'error': 'unauthorized'})
    conn = get_db()
    prod = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    if not prod: return jsonify({'error': 'not_found'})
        
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

@app.route('/pos')
def pos():
    if not session.get('user_id'): return redirect(url_for('login'))
    conn = get_db()
    products = conn.execute("SELECT * FROM products WHERE stock > 0").fetchall()
    conn.close()
    return render_template('pos.html', products=products)

@app.route('/product/new', methods=['GET', 'POST'])
def new_product():
    if not session.get('user_id'): return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        sizes = request.form.get('sizes', '')
        colors = request.form.get('colors', '')
        pur = int(request.form['purchase_price'])
        sal = int(request.form['sale_price'])
        stock = int(request.form['stock'])
        barcode = str(int(datetime.now().timestamp()))[-6:]
        now = datetime.now().strftime('%Y-%m-%d')
        
        conn = get_db()
        conn.execute("INSERT INTO products (barcode, name, sizes, colors, purchase_price, sale_price, stock, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                     (barcode, name, sizes, colors, pur, sal, stock, now, now))
        conn.commit()
        img = qrcode.make(barcode)
        img.save(f'static/barcodes/{barcode}.png')
        conn.close()
        flash('محصول ثبت شد', 'success')
        return redirect(url_for('new_product'))
    return render_template('new_product.html')

@app.route('/invoice/new/<inv_type>', methods=['GET', 'POST'])
def new_invoice(inv_type):
    if not session.get('user_id'): return redirect(url_for('login'))
    conn = get_db()
    if request.method == 'POST':
        cid = request.form.get('counterparty_id', 1)
        pid = request.form['product_id']
        qty = int(request.form['quantity'])
        price = int(request.form['unit_price'])
        total = qty * price
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        c = conn.cursor()
        c.execute("INSERT INTO invoices (type, counterparty_id, total_amount, date, status) VALUES (?,?,?,?,'paid')", (inv_type, cid, total, now))
        inv_id = c.lastrowid
        c.execute("INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price) VALUES (?,?,?,?)", (inv_id, pid, qty, price))
        
        if inv_type == 'buy':
            c.execute("UPDATE products SET stock = stock + ?, updated_at = ? WHERE id = ?", (qty, now, pid))
            c.execute("UPDATE accounts SET balance = balance - ? WHERE id = 1", (total,))
        else:
            c.execute("UPDATE products SET stock = stock - ?, updated_at = ? WHERE id = ?", (qty, now, pid))
            c.execute("UPDATE accounts SET balance = balance + ? WHERE id = 1", (total,))
            
        conn.commit()
        conn.close()
        flash('فاکتور ثبت شد', 'success')
        return redirect(url_for('dashboard'))

    prods = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template('new_invoice.html', products=prods, inv_type=inv_type)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8086, debug=True)
