#!/usr/bin/env python3
"""
Migration: add accepts_best_offer boolean column to items table
Safe to run multiple times.
"""

import mysql.connector
from mysql.connector import Error


def migrate():
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password=''  # adjust as needed
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("USE fastapi_db")

            def try_exec(sql: str, ok: str, dup_hint: str = "Duplicate"):
                try:
                    cursor.execute(sql)
                    print(f"✅ {ok}")
                except Error as e:
                    if dup_hint in str(e):
                        print(f"✅ {ok} (already exists)")
                    else:
                        print(f"❌ {ok} failed: {e}")

            # Add accepts_best_offer column
            try_exec(
                "ALTER TABLE items ADD COLUMN accepts_best_offer TINYINT(1) NOT NULL DEFAULT 0",
                "Added items.accepts_best_offer"
            )

            connection.commit()

    except Error as e:
        print(f"❌ Database error: {e}")
    finally:
        try:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("✅ Database connection closed")
        except NameError:
            pass


if __name__ == "__main__":
    migrate()

