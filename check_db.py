import sqlite3
conn = sqlite3.connect('usage.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(Sessions)")
for row in cursor.fetchall():
    print(row)
conn.close()
