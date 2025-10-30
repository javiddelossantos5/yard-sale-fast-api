#!/usr/bin/env python3
"""
Migration: create market_item_conversations and market_item_messages tables for messaging
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

            # Create market_item_conversations table
            try_exec(
                """
                CREATE TABLE market_item_conversations (
                  id CHAR(36) PRIMARY KEY,
                  item_id CHAR(36) NOT NULL,
                  participant1_id CHAR(36) NOT NULL,
                  participant2_id CHAR(36) NOT NULL,
                  created_at DATETIME,
                  updated_at DATETIME,
                  FOREIGN KEY (item_id) REFERENCES items(id),
                  FOREIGN KEY (participant1_id) REFERENCES users(id),
                  FOREIGN KEY (participant2_id) REFERENCES users(id)
                )
                """,
                "Created market_item_conversations table"
            )

            # Create market_item_messages table
            try_exec(
                """
                CREATE TABLE market_item_messages (
                  id CHAR(36) PRIMARY KEY,
                  content TEXT NOT NULL,
                  is_read TINYINT(1) DEFAULT 0,
                  created_at DATETIME,
                  conversation_id CHAR(36) NOT NULL,
                  sender_id CHAR(36) NOT NULL,
                  recipient_id CHAR(36) NOT NULL,
                  FOREIGN KEY (conversation_id) REFERENCES market_item_conversations(id),
                  FOREIGN KEY (sender_id) REFERENCES users(id),
                  FOREIGN KEY (recipient_id) REFERENCES users(id)
                )
                """,
                "Created market_item_messages table"
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

