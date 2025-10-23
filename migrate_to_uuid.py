#!/usr/bin/env python3
"""
Database migration script to convert user IDs from integers to UUIDs.
This is a complex migration that requires careful handling of foreign key relationships.

WARNING: This script will modify your database structure and data.
Make sure to backup your database before running this migration.
"""

import sys
import os
import uuid
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer
from sqlalchemy.orm import sessionmaker

# Add the current directory to Python path to import database module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL

def backup_database():
    """Create a backup of the current database"""
    print("Creating database backup...")
    # This would typically use mysqldump or similar
    # For now, we'll just warn the user
    print("⚠️  WARNING: Please backup your database before running this migration!")
    print("   You can use: mysqldump -u root fastapi_db > backup_$(date +%Y%m%d_%H%M%S).sql")
    
    response = input("Have you created a backup? (y/n): ").lower().strip()
    if response not in ['y', 'yes']:
        print("Migration cancelled. Please create a backup first.")
        sys.exit(1)

def get_user_mapping():
    """Get current users and create UUID mapping"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    with engine.connect() as connection:
        # Get all current users
        result = connection.execute(text("SELECT id, username FROM users ORDER BY id"))
        users = result.fetchall()
        
        # Create mapping from old ID to new UUID
        user_mapping = {}
        for old_id, username in users:
            new_uuid = str(uuid.uuid4())
            user_mapping[old_id] = new_uuid
            print(f"User {username} (ID: {old_id}) -> UUID: {new_uuid}")
        
        return user_mapping

def migrate_users_table(user_mapping):
    """Migrate the users table to use UUIDs"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    with engine.connect() as connection:
        # First, add a temporary column for the new UUID
        print("Adding temporary UUID column...")
        connection.execute(text("ALTER TABLE users ADD COLUMN new_id CHAR(36)"))
        
        # Update the new_id column with UUIDs
        print("Populating UUID column...")
        for old_id, new_uuid in user_mapping.items():
            connection.execute(text(
                "UPDATE users SET new_id = :new_uuid WHERE id = :old_id"
            ), {"new_uuid": new_uuid, "old_id": old_id})
        
        # Drop foreign key constraints temporarily
        print("Dropping foreign key constraints...")
        try:
            connection.execute(text("ALTER TABLE items DROP FOREIGN KEY items_ibfk_1"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE yard_sales DROP FOREIGN KEY yard_sales_ibfk_1"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE comments DROP FOREIGN KEY comments_ibfk_2"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE conversations DROP FOREIGN KEY conversations_ibfk_2"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE conversations DROP FOREIGN KEY conversations_ibfk_3"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE messages DROP FOREIGN KEY messages_ibfk_2"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE messages DROP FOREIGN KEY messages_ibfk_3"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE user_ratings DROP FOREIGN KEY user_ratings_ibfk_1"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE user_ratings DROP FOREIGN KEY user_ratings_ibfk_2"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE reports DROP FOREIGN KEY reports_ibfk_1"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE reports DROP FOREIGN KEY reports_ibfk_2"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE verifications DROP FOREIGN KEY verifications_ibfk_1"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE visited_yard_sales DROP FOREIGN KEY visited_yard_sales_ibfk_1"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE notifications DROP FOREIGN KEY notifications_ibfk_1"))
        except:
            pass
        try:
            connection.execute(text("ALTER TABLE notifications DROP FOREIGN KEY notifications_ibfk_2"))
        except:
            pass
        
        # Drop the old primary key
        print("Dropping old primary key...")
        connection.execute(text("ALTER TABLE users DROP PRIMARY KEY"))
        
        # Drop the old id column
        print("Dropping old id column...")
        connection.execute(text("ALTER TABLE users DROP COLUMN id"))
        
        # Rename new_id to id and make it primary key
        print("Setting up new primary key...")
        connection.execute(text("ALTER TABLE users CHANGE COLUMN new_id id CHAR(36) NOT NULL PRIMARY KEY"))
        
        connection.commit()
        print("Users table migration completed!")

def migrate_foreign_key_tables(user_mapping):
    """Migrate all tables with foreign keys to users"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    tables_to_migrate = [
        ("items", "owner_id"),
        ("yard_sales", "owner_id"),
        ("comments", "user_id"),
        ("conversations", "participant1_id"),
        ("conversations", "participant2_id"),
        ("messages", "sender_id"),
        ("messages", "recipient_id"),
        ("user_ratings", "reviewer_id"),
        ("user_ratings", "rated_user_id"),
        ("reports", "reporter_id"),
        ("reports", "reported_user_id"),
        ("verifications", "user_id"),
        ("visited_yard_sales", "user_id"),
        ("notifications", "user_id"),
        ("notifications", "related_user_id")
    ]
    
    with engine.connect() as connection:
        for table_name, column_name in tables_to_migrate:
            print(f"Migrating {table_name}.{column_name}...")
            
            # Add temporary column
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN new_{column_name} CHAR(36)"))
            
            # Update with new UUIDs
            for old_id, new_uuid in user_mapping.items():
                connection.execute(text(f"""
                    UPDATE {table_name} 
                    SET new_{column_name} = :new_uuid 
                    WHERE {column_name} = :old_id
                """), {"new_uuid": new_uuid, "old_id": old_id})
            
            # Drop old column and rename new one
            connection.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))
            connection.execute(text(f"ALTER TABLE {table_name} CHANGE COLUMN new_{column_name} {column_name} CHAR(36)"))
            
            # Add foreign key constraint
            connection.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD CONSTRAINT {table_name}_{column_name}_fk 
                FOREIGN KEY ({column_name}) REFERENCES users(id)
            """))
        
        connection.commit()
        print("Foreign key tables migration completed!")

def verify_migration():
    """Verify the migration was successful"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    with engine.connect() as connection:
        # Check users table
        result = connection.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar()
        print(f"Users table has {user_count} records")
        
        # Check that all user IDs are valid UUIDs
        result = connection.execute(text("SELECT id FROM users LIMIT 5"))
        sample_ids = result.fetchall()
        print("Sample user IDs:")
        for (user_id,) in sample_ids:
            print(f"  {user_id}")
            try:
                uuid.UUID(user_id)
                print(f"    ✅ Valid UUID")
            except ValueError:
                print(f"    ❌ Invalid UUID")
        
        # Check foreign key relationships
        print("\nChecking foreign key relationships...")
        tables_to_check = [
            ("items", "owner_id"),
            ("yard_sales", "owner_id"),
            ("comments", "user_id")
        ]
        
        for table_name, column_name in tables_to_check:
            result = connection.execute(text(f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE {column_name} NOT IN (SELECT id FROM users)
            """))
            orphaned_count = result.scalar()
            if orphaned_count == 0:
                print(f"  ✅ {table_name}.{column_name} - All references valid")
            else:
                print(f"  ❌ {table_name}.{column_name} - {orphaned_count} orphaned references")

def main():
    """Main migration function"""
    print("UUID Migration Script")
    print("=" * 50)
    print()
    
    try:
        # Step 1: Backup
        backup_database()
        
        # Step 2: Get user mapping
        print("\nStep 1: Creating user ID mapping...")
        user_mapping = get_user_mapping()
        
        # Step 3: Migrate users table
        print("\nStep 2: Migrating users table...")
        migrate_users_table(user_mapping)
        
        # Step 4: Migrate foreign key tables
        print("\nStep 3: Migrating foreign key tables...")
        migrate_foreign_key_tables(user_mapping)
        
        # Step 5: Verify migration
        print("\nStep 4: Verifying migration...")
        verify_migration()
        
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Test your application thoroughly")
        print("2. Update any hardcoded user IDs in your code")
        print("3. Update your API documentation")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Please restore from your backup and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
