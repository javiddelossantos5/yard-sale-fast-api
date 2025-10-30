#!/usr/bin/env python3
"""
Migration: add original_price and last_price_change_date to items table for price reduction tracking
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

            # Add price tracking columns
            try_exec(
                "ALTER TABLE items ADD COLUMN original_price FLOAT NULL",
                "Added items.original_price"
            )
            try_exec(
                "ALTER TABLE items ADD COLUMN last_price_change_date DATETIME NULL",
                "Added items.last_price_change_date"
            )

            # For existing items, set original_price to current price
            try_exec(
                "UPDATE items SET original_price = price WHERE original_price IS NULL",
                "Set original_price for existing items"
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

