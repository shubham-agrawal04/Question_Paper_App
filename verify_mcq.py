
import sqlite3
import sys
import os
import requests

# Add local directory to path to import app
sys.path.append(os.getcwd())

from app import init_database, DATABASE_PATH

def main():
    print("Running init_database()...")
    init_database()
    
    print("Checking database schema...")
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='question_answers'")
        table = cursor.fetchone()
        
        if table:
            print("✅ 'question_answers' table exists.")
            
            cursor.execute("PRAGMA table_info(question_answers)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'question_id' in columns and 'correct_answer' in columns:
                print("✅ Schema is correct.")
            else:
                print("❌ Schema is missing columns.")
        else:
            print("❌ 'question_answers' table does NOT exist.")
            
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    main()
