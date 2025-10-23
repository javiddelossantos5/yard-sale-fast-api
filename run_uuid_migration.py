#!/usr/bin/env python3
"""
Run UUID migration without interactive prompts.
"""

import sys
import os
import uuid
from sqlalchemy import create_engine, text

# Add the current directory to Python path to import database module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL

def get_current_users():
    """Get all current users from the database"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    with engine.connect() as connection:
        result = connection.execute(text("SELECT id, username, email FROM users ORDER BY id"))
        users = result.fetchall()
        
        print(f"Found {len(users)} users in the database:")
        for user_id, username, email in users:
            print(f"  ID: {user_id}, Username: {username}, Email: {email}")
        
        return users

def create_user_mapping(users):
    """Create mapping from old integer IDs to new UUIDs"""
    user_mapping = {}
    
    print("\nCreating UUID mapping:")
    for old_id, username, email in users:
        new_uuid = str(uuid.uuid4())
        user_mapping[old_id] = new_uuid
        print(f"  {username} (ID: {old_id}) -> UUID: {new_uuid}")
    
    return user_mapping

def migrate_users_table(user_mapping):
    """Migrate the users table to use UUIDs"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    with engine.connect() as connection:
        print("\nStep 1: Adding temporary UUID column...")
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN new_id CHAR(36)"))
            print("✅ Added temporary UUID column")
        except Exception as e:
            print(f"❌ Error adding UUID column: {e}")
            return False
        
        print("\nStep 2: Populating UUID column...")
        for old_id, new_uuid in user_mapping.items():
            try:
                connection.execute(text(
                    "UPDATE users SET new_id = :new_uuid WHERE id = :old_id"
                ), {"new_uuid": new_uuid, "old_id": old_id})
                print(f"  ✅ Updated user ID {old_id} -> {new_uuid}")
            except Exception as e:
                print(f"  ❌ Error updating user {old_id}: {e}")
                return False
        
        print("\nStep 3: Dropping foreign key constraints...")
        # List of foreign key constraints to drop
        fk_constraints = [
            ("items", "items_ibfk_1"),
            ("yard_sales", "yard_sales_ibfk_1"),
            ("comments", "comments_ibfk_2"),
            ("conversations", "conversations_ibfk_2"),
            ("conversations", "conversations_ibfk_3"),
            ("messages", "messages_ibfk_2"),
            ("messages", "messages_ibfk_3"),
            ("user_ratings", "user_ratings_ibfk_1"),
            ("user_ratings", "user_ratings_ibfk_2"),
            ("reports", "reports_ibfk_1"),
            ("reports", "reports_ibfk_2"),
            ("verifications", "verifications_ibfk_1"),
            ("visited_yard_sales", "visited_yard_sales_ibfk_1"),
            ("notifications", "notifications_ibfk_1"),
            ("notifications", "notifications_ibfk_2")
        ]
        
        for table, constraint in fk_constraints:
            try:
                connection.execute(text(f"ALTER TABLE {table} DROP FOREIGN KEY {constraint}"))
                print(f"  ✅ Dropped constraint {constraint}")
            except Exception as e:
                print(f"  ⚠️  Could not drop constraint {constraint}: {e}")
        
        print("\nStep 4: Dropping old primary key...")
        try:
            connection.execute(text("ALTER TABLE users DROP PRIMARY KEY"))
            print("✅ Dropped old primary key")
        except Exception as e:
            print(f"❌ Error dropping primary key: {e}")
            return False
        
        print("\nStep 5: Dropping old ID column...")
        try:
            connection.execute(text("ALTER TABLE users DROP COLUMN id"))
            print("✅ Dropped old ID column")
        except Exception as e:
            print(f"❌ Error dropping ID column: {e}")
            return False
        
        print("\nStep 6: Setting up new UUID primary key...")
        try:
            connection.execute(text("ALTER TABLE users CHANGE COLUMN new_id id CHAR(36) NOT NULL PRIMARY KEY"))
            print("✅ Set up new UUID primary key")
        except Exception as e:
            print(f"❌ Error setting up new primary key: {e}")
            return False
        
        connection.commit()
        print("\n✅ Users table migration completed!")
        return True

def migrate_foreign_key_tables(user_mapping):
    """Migrate all tables with foreign keys to users"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    # Tables and their user foreign key columns
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
            print(f"\nMigrating {table_name}.{column_name}...")
            
            try:
                # Check if table exists and has the column
                result = connection.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_schema = 'fastapi_db' 
                    AND table_name = '{table_name}' 
                    AND column_name = '{column_name}'
                """))
                
                if result.scalar() == 0:
                    print(f"  ⚠️  Table {table_name} or column {column_name} does not exist, skipping")
                    continue
                
                # Add temporary column
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN new_{column_name} CHAR(36)"))
                print(f"  ✅ Added temporary column")
                
                # Update with new UUIDs
                updated_count = 0
                for old_id, new_uuid in user_mapping.items():
                    result = connection.execute(text(f"""
                        UPDATE {table_name} 
                        SET new_{column_name} = :new_uuid 
                        WHERE {column_name} = :old_id
                    """), {"new_uuid": new_uuid, "old_id": old_id})
                    updated_count += result.rowcount
                
                print(f"  ✅ Updated {updated_count} records")
                
                # Drop old column and rename new one
                connection.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))
                connection.execute(text(f"ALTER TABLE {table_name} CHANGE COLUMN new_{column_name} {column_name} CHAR(36)"))
                print(f"  ✅ Renamed column")
                
                # Add foreign key constraint
                connection.execute(text(f"""
                    ALTER TABLE {table_name} 
                    ADD CONSTRAINT {table_name}_{column_name}_fk 
                    FOREIGN KEY ({column_name}) REFERENCES users(id)
                """))
                print(f"  ✅ Added foreign key constraint")
                
            except Exception as e:
                print(f"  ❌ Error migrating {table_name}.{column_name}: {e}")
                return False
        
        connection.commit()
        print("\n✅ Foreign key tables migration completed!")
        return True

def verify_migration():
    """Verify the migration was successful"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    with engine.connect() as connection:
        print("\nVerifying migration...")
        
        # Check users table structure
        result = connection.execute(text("DESCRIBE users"))
        columns = result.fetchall()
        
        print("Users table structure:")
        for col in columns:
            print(f"  {col[0]} - {col[1]} - {col[2]} - {col[3]} - {col[4]} - {col[5]}")
        
        # Check that ID column is CHAR(36)
        id_column = next((col for col in columns if col[0] == 'id'), None)
        if id_column and 'char(36)' in id_column[1].lower():
            print("✅ ID column is properly set to CHAR(36)")
        else:
            print("❌ ID column is not CHAR(36)")
            return False
        
        # Check sample user IDs
        result = connection.execute(text("SELECT id, username FROM users LIMIT 3"))
        users = result.fetchall()
        
        print("\nSample user IDs:")
        for user_id, username in users:
            print(f"  {username}: {user_id}")
            try:
                uuid.UUID(user_id)
                print(f"    ✅ Valid UUID")
            except ValueError:
                print(f"    ❌ Invalid UUID")
                return False
        
        print("\n✅ Migration verification completed successfully!")
        return True

def main():
    """Main migration function"""
    print("UUID Migration Script")
    print("=" * 50)
    print()
    
    try:
        # Step 1: Get current users
        print("Getting current users...")
        users = get_current_users()
        
        if not users:
            print("No users found in database. Nothing to migrate.")
            return
        
        # Step 2: Create user mapping
        user_mapping = create_user_mapping(users)
        
        # Step 3: Migrate users table
        print("\n" + "="*50)
        print("MIGRATING USERS TABLE")
        print("="*50)
        if not migrate_users_table(user_mapping):
            print("❌ Users table migration failed!")
            return
        
        # Step 4: Migrate foreign key tables
        print("\n" + "="*50)
        print("MIGRATING FOREIGN KEY TABLES")
        print("="*50)
        if not migrate_foreign_key_tables(user_mapping):
            print("❌ Foreign key tables migration failed!")
            return
        
        # Step 5: Verify migration
        print("\n" + "="*50)
        print("VERIFYING MIGRATION")
        print("="*50)
        if not verify_migration():
            print("❌ Migration verification failed!")
            return
        
        print("\n" + "="*50)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*50)
        print("\nYour database now uses UUIDs for user IDs.")
        print("You can now start your FastAPI application with UUID support.")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
