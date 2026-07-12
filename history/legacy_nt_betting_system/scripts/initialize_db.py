#!/usr/bin/env python3
"""
Initialize the bets.db database from schema.sql
"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "bets.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()

    cursor.executescript(schema)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    initialize_database()