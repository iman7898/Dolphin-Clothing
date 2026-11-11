import re
import os

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. تغییر ایمپورت‌ها
if 'import libsql' not in code:
    code = code.replace('import sqlite3', 'import sqlite3\nimport libsql\nimport os\nfrom dotenv import load_dotenv\nload_dotenv()')

# 2. پیدا کردن تابع get_db و جایگزینی با نسخه Turso
pattern = r"def get_db\(\):.*?return conn"
new_db_func = """def get_db():
    conn = libsql.connect(
        database="local.db",
        sync_url=os.getenv("TURSO_DATABASE_URL"),
        auth_token=os.getenv("TURSO_AUTH_TOKEN"),
        sync_interval=60
    )
    conn.sync()
    conn.row_factory = sqlite3.Row
    return conn"""

if re.search(pattern, code, flags=re.DOTALL):
    code = re.sub(pattern, new_db_func, code, flags=re.DOTALL)
    print("✅ تابع get_db با موفقیت به Turso وصل شد.")
else:
    print("⚠️ تابع get_db پیدا نشد. لطفا دستی چک کنید.")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

# 3. ساخت فایل requirements.txt
with open('requirements.txt', 'w') as f:
    f.write("Flask\nqrcode\npillow\ngunicorn\nlibsql\npython-dotenv\n")

print("✅ فایل requirements.txt هم آپدیت شد.")
