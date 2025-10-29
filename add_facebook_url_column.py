#!/usr/bin/env python3
"""
Script to add the facebook_url column to existing yard_sales as NULLable
"""

import mysql.connector
from mysql.connector import Error


def add_facebook_url_column():
    try:
        # Connect to MySQL
        connection = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password=''
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Use the database
            cursor.execute("USE fastapi_db")

            # Add the facebook_url column if it doesn't exist
            try:
                cursor.execute(
                    """
                    ALTER TABLE yard_sales
                    ADD COLUMN facebook_url VARCHAR(500) NULL
                    """
                )
                print("✅ Added facebook_url column to yard_sales table")
            except Error as e:
                if "Duplicate column name" in str(e):
                    print("✅ facebook_url column already exists")
                else:
                    print(f"❌ Error adding facebook_url column: {e}")

            connection.commit()

    except Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("✅ Database connection closed")


if __name__ == "__main__":
    add_facebook_url_column()


