#!/usr/bin/env python3
"""
Migration: add venmo_url, facebook_url to items and create market_item_comments and watched_items tables
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

            # Add columns to items
            try_exec("ALTER TABLE items ADD COLUMN venmo_url VARCHAR(500) NULL", "Added items.venmo_url")
            try_exec("ALTER TABLE items ADD COLUMN facebook_url VARCHAR(500) NULL", "Added items.facebook_url")

            # Create market_item_comments
            try_exec(
                """
                CREATE TABLE market_item_comments (
                  id CHAR(36) PRIMARY KEY,
                  content TEXT NOT NULL,
                  created_at DATETIME,
                  updated_at DATETIME,
                  item_id CHAR(36) NOT NULL,
                  user_id CHAR(36) NOT NULL
                )
                """,
                "Created market_item_comments"
            )

            # Create watched_items with unique constraint
            try_exec(
                """
                CREATE TABLE watched_items (
                  id CHAR(36) PRIMARY KEY,
                  created_at DATETIME,
                  user_id CHAR(36) NOT NULL,
                  item_id CHAR(36) NOT NULL,
                  UNIQUE KEY unique_user_item_watch (user_id, item_id)
                )
                """,
                "Created watched_items"
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


