import sqlite3
import os

db_path = r"c:\Users\Administrator\Documents\trae_projects\test\student_management\data\student_management.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print("All tables:", tables)

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"Table '{table}': {count} records")

print("\nDeleting student data from performance testing...")

cursor.execute("DELETE FROM students")
deleted = cursor.rowcount
conn.commit()
print(f"Deleted {deleted} records from 'students' table")

conn.close()
print("Done!")
