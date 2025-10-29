#!/usr/bin/env python3
"""
Add marketplace columns to the items table (safe, idempotent)
"""

import mysql.connector
from mysql.connector import Error


def add_market_item_fields():
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password=''  # adjust if needed
        )

        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("USE fastapi_db")

            def try_alter(sql: str, success: str, duplicate_hint: str):
                try:
                    cursor.execute(sql)
                    print(success)
                except Error as e:
                    if duplicate_hint in str(e):
                        print(f"✅ {success} (already exists)")
                    else:
                        print(f"❌ {success} failed: {e}")

            try_alter(
                "ALTER TABLE items ADD COLUMN is_public TINYINT(1) NOT NULL DEFAULT 1",
                "Added is_public",
                "Duplicate column name"
            )
            try_alter(
                "ALTER TABLE items ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'",
                "Added status",
                "Duplicate column name"
            )
            try_alter(
                "ALTER TABLE items ADD COLUMN category VARCHAR(100) NULL",
                "Added category",
                "Duplicate column name"
            )
            try_alter(
                "ALTER TABLE items ADD COLUMN photos JSON NULL",
                "Added photos",
                "Duplicate column name"
            )
            try_alter(
                "ALTER TABLE items ADD COLUMN featured_image VARCHAR(500) NULL",
                "Added featured_image",
                "Duplicate column name"
            )
            try_alter(
                "ALTER TABLE items ADD COLUMN price_range VARCHAR(50) NULL",
                "Added price_range",
                "Duplicate column name"
            )
            try_alter(
                "ALTER TABLE items ADD COLUMN payment_methods JSON NULL",
                "Added payment_methods",
                "Duplicate column name"
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
    add_market_item_fields()


