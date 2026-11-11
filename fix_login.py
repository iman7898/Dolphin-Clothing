import re

# 1. آپدیت کدهای پایتون برای ورود با نقش و رمز عبور
with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_login_route = """
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        password = request.form.get('password')
        
        # بررسی رمز عبور بر اساس نقش انتخاب شده
        if role == 'admin' and password == 'iman7898':
            session['user_id'] = 1
            session['role'] = 'admin'
            session['username'] = 'مدیر'
            return redirect(url_for('dashboard'))
        elif role == 'seller' and password == 'shok12':
            session['user_id'] = 2
            session['role'] = 'seller'
            session['username'] = 'فروشنده'
            return redirect(url_for('dashboard'))
        else:
            flash('❌ رمز عبور اشتباه است!', 'danger')
            
    return render_template('login.html')
"""

# پیدا کردن مسیر لاگین قبلی و جایگزینی
pattern = r"@app\.route\('/login', methods=\['GET', 'POST'\]\).*?(?=@app\.route|if __name__)"
if re.search(pattern, code, flags=re.DOTALL):
    code = re.sub(pattern, new_login_route, code, flags=re.DOTALL)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print("✅ کدهای پایتون لاگین آپدیت شدند.")
else:
    print("⚠️ مسیر لاگین پیدا نشد.")
