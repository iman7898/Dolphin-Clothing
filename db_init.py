import sqlite3
def init_db():
    conn = sqlite3.connect('dolphin.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user')''')
    c.execute('''CREATE TABLE counterparties (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, type TEXT)''')
    c.execute('''CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT UNIQUE,
        name TEXT NOT NULL,
        category TEXT,
        sizes TEXT, -- مثلا S,M,L
        colors TEXT, -- مثلا قرمز,آبی
        purchase_price INTEGER DEFAULT 0,
        sale_price INTEGER DEFAULT 0,
        stock INTEGER DEFAULT 0,
        image_url TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT, counterparty_id INTEGER, total_amount INTEGER, discount INTEGER, date TEXT, status TEXT
    )''')
    c.execute('''CREATE TABLE invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER, product_id INTEGER, size TEXT, color TEXT, quantity INTEGER, unit_price INTEGER
    )''')
    c.execute('''CREATE TABLE returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER, product_id INTEGER, quantity INTEGER, amount INTEGER, date TEXT
    )''')
    c.execute('''CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT, balance INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE ledger (id INTEGER PRIMARY KEY, date TEXT, description TEXT, debit_account INTEGER, credit_account INTEGER, amount INTEGER, ref_type TEXT, ref_id INTEGER)''')
    
    c.execute("INSERT INTO accounts (name, balance) VALUES ('صندوق', 0)")
    c.execute("INSERT INTO accounts (name, balance) VALUES ('بانک', 0)")
    c.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    conn.commit()
    conn.close()
if __name__ == '__main__': init_db()
