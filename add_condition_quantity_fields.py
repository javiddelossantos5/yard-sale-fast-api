#!/usr/bin/env python3
"""
Add condition and quantity columns to the items table (safe, idempotent)
"""

import mysql.connector
from mysql.connector import Error


def add_condition_quantity_fields():
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
                    print(f"✅ {success}")
                except Error as e:
                    if duplicate_hint in str(e):
                        print(f"✅ {success} (already exists)")
                    else:
                        print(f"❌ {success} failed: {e}")

            try_alter(
                "ALTER TABLE items ADD COLUMN `condition` VARCHAR(50) NULL",
                "Added condition column",
                "Duplicate column name"
            )
            try_alter(
                "ALTER TABLE items ADD COLUMN quantity INT NULL",
                "Added quantity column",
                "Duplicate column name"
            )

            connection.commit()
            print("\n✅ Migration completed successfully!")

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
    add_condition_quantity_fields()

