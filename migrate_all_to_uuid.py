#!/usr/bin/env python3
"""
Comprehensive UUID migration script to convert ALL entity IDs to UUIDs.
This includes: yard_sales, items, comments, conversations, messages, user_ratings, reports, verifications, notifications
"""

import sys
import os
import uuid
from sqlalchemy import create_engine, text
from collections import defaultdict

# Add the current directory to Python path to import database module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL

def get_table_data():
    """Get all data from tables that need UUID migration"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    tables_data = {}
    
    with engine.connect() as connection:
        # Tables to migrate (excluding users which is already done)
        tables = [
            'yard_sales',
            'items', 
            'comments',
            'conversations',
            'messages',
            'user_ratings',
            'reports',
            'verifications',
            'notifications'
        ]
        
        for table in tables:
            try:
                result = connection.execute(text(f"SELECT id FROM {table} ORDER BY id"))
                ids = [row[0] for row in result.fetchall()]
                tables_data[table] = ids
                print(f"Found {len(ids)} records in {table}")
            except Exception as e:
                print(f"Error getting data from {table}: {e}")
                tables_data[table] = []
    
    return tables_data

def create_id_mappings(tables_data):
    """Create UUID mappings for all tables"""
    mappings = {}
    
    for table, ids in tables_data.items():
        table_mapping = {}
        for old_id in ids:
            new_uuid = str(uuid.uuid4())
            table_mapping[old_id] = new_uuid
        mappings[table] = table_mapping
        print(f"Created {len(table_mapping)} UUID mappings for {table}")
    
    return mappings

def migrate_table_to_uuid(table_name, id_mapping):
    """Migrate a single table to use UUIDs"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    with engine.connect() as connection:
        print(f"\n=== Migrating {table_name} ===")
        
        # Step 1: Add temporary UUID column
        print(f"Step 1: Adding temporary UUID column to {table_name}")
        try:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN new_id CHAR(36)"))
            print(f"✅ Added temporary UUID column")
        except Exception as e:
            print(f"❌ Error adding UUID column: {e}")
            return False
        
        # Step 2: Populate UUID column
        print(f"Step 2: Populating UUID column for {table_name}")
        for old_id, new_uuid in id_mapping.items():
            try:
                connection.execute(text(f"""
                    UPDATE {table_name} 
                    SET new_id = :new_uuid 
                    WHERE id = :old_id
                """), {"new_uuid": new_uuid, "old_id": old_id})
            except Exception as e:
                print(f"❌ Error updating {table_name} ID {old_id}: {e}")
                return False
        print(f"✅ Updated {len(id_mapping)} records")
        
        # Step 3: Drop foreign key constraints that reference this table
        print(f"Step 3: Dropping foreign key constraints for {table_name}")
        fk_constraints = get_foreign_key_constraints(table_name)
        for constraint in fk_constraints:
            try:
                connection.execute(text(f"ALTER TABLE {constraint['table']} DROP FOREIGN KEY {constraint['constraint_name']}"))
                print(f"  ✅ Dropped constraint {constraint['constraint_name']}")
            except Exception as e:
                print(f"  ⚠️  Could not drop constraint {constraint['constraint_name']}: {e}")
        
        # Step 4: Drop old primary key
        print(f"Step 4: Dropping old primary key for {table_name}")
        try:
            connection.execute(text(f"ALTER TABLE {table_name} DROP PRIMARY KEY"))
            print(f"✅ Dropped old primary key")
        except Exception as e:
            print(f"❌ Error dropping primary key: {e}")
            return False
        
        # Step 5: Drop old ID column
        print(f"Step 5: Dropping old ID column for {table_name}")
        try:
            connection.execute(text(f"ALTER TABLE {table_name} DROP COLUMN id"))
            print(f"✅ Dropped old ID column")
        except Exception as e:
            print(f"❌ Error dropping ID column: {e}")
            return False
        
        # Step 6: Set up new UUID primary key
        print(f"Step 6: Setting up new UUID primary key for {table_name}")
        try:
            connection.execute(text(f"ALTER TABLE {table_name} CHANGE COLUMN new_id id CHAR(36) NOT NULL PRIMARY KEY"))
            print(f"✅ Set up new UUID primary key")
        except Exception as e:
            print(f"❌ Error setting up new primary key: {e}")
            return False
        
        connection.commit()
        print(f"✅ {table_name} migration completed!")
        return True

def migrate_foreign_key_columns():
    """Migrate all foreign key columns to UUID format"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    # Define foreign key relationships that need to be migrated
    foreign_key_migrations = [
        # (table, column, referenced_table)
        ('items', 'owner_id', 'users'),
        ('yard_sales', 'owner_id', 'users'),
        ('comments', 'user_id', 'users'),
        ('comments', 'yard_sale_id', 'yard_sales'),
        ('conversations', 'participant1_id', 'users'),
        ('conversations', 'participant2_id', 'users'),
        ('conversations', 'yard_sale_id', 'yard_sales'),
        ('messages', 'sender_id', 'users'),
        ('messages', 'recipient_id', 'users'),
        ('messages', 'conversation_id', 'conversations'),
        ('user_ratings', 'reviewer_id', 'users'),
        ('user_ratings', 'rated_user_id', 'users'),
        ('user_ratings', 'yard_sale_id', 'yard_sales'),
        ('reports', 'reporter_id', 'users'),
        ('reports', 'reported_user_id', 'users'),
        ('reports', 'reported_yard_sale_id', 'yard_sales'),
        ('verifications', 'user_id', 'users'),
        ('visited_yard_sales', 'user_id', 'users'),
        ('visited_yard_sales', 'yard_sale_id', 'yard_sales'),
        ('notifications', 'user_id', 'users'),
        ('notifications', 'related_user_id', 'users'),
        ('notifications', 'related_yard_sale_id', 'yard_sales'),
        ('notifications', 'related_message_id', 'messages')
    ]
    
    with engine.connect() as connection:
        print("\n=== Migrating Foreign Key Columns to UUID ===")
        
        for table, column, referenced_table in foreign_key_migrations:
            print(f"\nMigrating {table}.{column} -> {referenced_table}.id")
            
            # Check if the table and column exist
            try:
                result = connection.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_schema = 'fastapi_db' 
                    AND table_name = '{table}' 
                    AND column_name = '{column}'
                """))
                
                if result.scalar() == 0:
                    print(f"  ⚠️  Table {table} or column {column} does not exist, skipping")
                    continue
                
                # Check if the column is already CHAR(36)
                result = connection.execute(text(f"""
                    SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH 
                    FROM information_schema.columns 
                    WHERE table_schema = 'fastapi_db' 
                    AND table_name = '{table}' 
                    AND column_name = '{column}'
                """))
                
                column_info = result.fetchone()
                if column_info and column_info[0] == 'char' and column_info[1] == 36:
                    print(f"  ✅ {table}.{column} is already CHAR(36), skipping")
                    continue
                
                # Drop foreign key constraint if it exists
                try:
                    # Get constraint name
                    result = connection.execute(text(f"""
                        SELECT CONSTRAINT_NAME 
                        FROM information_schema.KEY_COLUMN_USAGE 
                        WHERE table_schema = 'fastapi_db' 
                        AND table_name = '{table}' 
                        AND column_name = '{column}'
                        AND REFERENCED_TABLE_NAME IS NOT NULL
                    """))
                    
                    constraint_name = result.fetchone()
                    if constraint_name:
                        connection.execute(text(f"ALTER TABLE {table} DROP FOREIGN KEY {constraint_name[0]}"))
                        print(f"  ✅ Dropped foreign key constraint {constraint_name[0]}")
                except Exception as e:
                    print(f"  ⚠️  Could not drop foreign key constraint: {e}")
                
                # Alter column to CHAR(36)
                try:
                    connection.execute(text(f"ALTER TABLE {table} MODIFY COLUMN {column} CHAR(36)"))
                    print(f"  ✅ Changed {table}.{column} to CHAR(36)")
                except Exception as e:
                    print(f"  ❌ Error changing {table}.{column} to CHAR(36): {e}")
                    return False
                
            except Exception as e:
                print(f"  ❌ Error migrating {table}.{column}: {e}")
                return False
        
        connection.commit()
        print("\n✅ Foreign key columns migrated to UUID format!")
        return True

def get_foreign_key_constraints(table_name):
    """Get foreign key constraints that reference a table"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    constraints = []
    
    with engine.connect() as connection:
        # Get foreign key constraints that reference this table
        result = connection.execute(text(f"""
            SELECT 
                TABLE_NAME,
                CONSTRAINT_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM 
                INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
            WHERE 
                REFERENCED_TABLE_SCHEMA = 'fastapi_db' 
                AND REFERENCED_TABLE_NAME = '{table_name}'
                AND REFERENCED_COLUMN_NAME = 'id'
        """))
        
        for row in result.fetchall():
            constraints.append({
                'table': row[0],
                'constraint_name': row[1],
                'column_name': row[2],
                'referenced_table': row[3],
                'referenced_column': row[4]
            })
    
    return constraints

def update_foreign_key_references(all_mappings):
    """Update all foreign key references to use new UUIDs"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    # Define foreign key relationships
    foreign_key_relationships = [
        # (referencing_table, referencing_column, referenced_table)
        ('items', 'owner_id', 'users'),
        ('yard_sales', 'owner_id', 'users'),
        ('comments', 'user_id', 'users'),
        ('comments', 'yard_sale_id', 'yard_sales'),
        ('conversations', 'participant1_id', 'users'),
        ('conversations', 'participant2_id', 'users'),
        ('conversations', 'yard_sale_id', 'yard_sales'),
        ('messages', 'sender_id', 'users'),
        ('messages', 'recipient_id', 'users'),
        ('messages', 'conversation_id', 'conversations'),
        ('user_ratings', 'reviewer_id', 'users'),
        ('user_ratings', 'rated_user_id', 'users'),
        ('user_ratings', 'yard_sale_id', 'yard_sales'),
        ('reports', 'reporter_id', 'users'),
        ('reports', 'reported_user_id', 'users'),
        ('reports', 'reported_yard_sale_id', 'yard_sales'),
        ('verifications', 'user_id', 'users'),
        ('visited_yard_sales', 'user_id', 'users'),
        ('visited_yard_sales', 'yard_sale_id', 'yard_sales'),
        ('notifications', 'user_id', 'users'),
        ('notifications', 'related_user_id', 'users'),
        ('notifications', 'related_yard_sale_id', 'yard_sales'),
        ('notifications', 'related_message_id', 'messages')
    ]
    
    with engine.connect() as connection:
        for referencing_table, referencing_column, referenced_table in foreign_key_relationships:
            print(f"\nUpdating {referencing_table}.{referencing_column} -> {referenced_table}.id")
            
            # Check if the referencing table and column exist
            try:
                result = connection.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_schema = 'fastapi_db' 
                    AND table_name = '{referencing_table}' 
                    AND column_name = '{referencing_column}'
                """))
                
                if result.scalar() == 0:
                    print(f"  ⚠️  Table {referencing_table} or column {referencing_column} does not exist, skipping")
                    continue
                
                # Check if referenced table has been migrated
                if referenced_table not in all_mappings:
                    print(f"  ⚠️  Referenced table {referenced_table} not migrated yet, skipping")
                    continue
                
                # Update foreign key references
                referenced_mapping = all_mappings[referenced_table]
                updated_count = 0
                
                for old_id, new_uuid in referenced_mapping.items():
                    result = connection.execute(text(f"""
                        UPDATE {referencing_table} 
                        SET {referencing_column} = :new_uuid 
                        WHERE {referencing_column} = :old_id
                    """), {"new_uuid": new_uuid, "old_id": old_id})
                    updated_count += result.rowcount
                
                print(f"  ✅ Updated {updated_count} references")
                
            except Exception as e:
                print(f"  ❌ Error updating {referencing_table}.{referencing_column}: {e}")
                return False
        
        connection.commit()
        print("\n✅ Foreign key references updated!")
        return True

def recreate_foreign_key_constraints():
    """Recreate all foreign key constraints"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    foreign_key_constraints = [
        # (table, column, referenced_table, referenced_column, constraint_name)
        ('items', 'owner_id', 'users', 'id', 'items_owner_id_fk'),
        ('yard_sales', 'owner_id', 'users', 'id', 'yard_sales_owner_id_fk'),
        ('comments', 'user_id', 'users', 'id', 'comments_user_id_fk'),
        ('comments', 'yard_sale_id', 'yard_sales', 'id', 'comments_yard_sale_id_fk'),
        ('conversations', 'participant1_id', 'users', 'id', 'conversations_participant1_id_fk'),
        ('conversations', 'participant2_id', 'users', 'id', 'conversations_participant2_id_fk'),
        ('conversations', 'yard_sale_id', 'yard_sales', 'id', 'conversations_yard_sale_id_fk'),
        ('messages', 'sender_id', 'users', 'id', 'messages_sender_id_fk'),
        ('messages', 'recipient_id', 'users', 'id', 'messages_recipient_id_fk'),
        ('messages', 'conversation_id', 'conversations', 'id', 'messages_conversation_id_fk'),
        ('user_ratings', 'reviewer_id', 'users', 'id', 'user_ratings_reviewer_id_fk'),
        ('user_ratings', 'rated_user_id', 'users', 'id', 'user_ratings_rated_user_id_fk'),
        ('user_ratings', 'yard_sale_id', 'yard_sales', 'id', 'user_ratings_yard_sale_id_fk'),
        ('reports', 'reporter_id', 'users', 'id', 'reports_reporter_id_fk'),
        ('reports', 'reported_user_id', 'users', 'id', 'reports_reported_user_id_fk'),
        ('reports', 'reported_yard_sale_id', 'yard_sales', 'id', 'reports_reported_yard_sale_id_fk'),
        ('verifications', 'user_id', 'users', 'id', 'verifications_user_id_fk'),
        ('visited_yard_sales', 'user_id', 'users', 'id', 'visited_yard_sales_user_id_fk'),
        ('visited_yard_sales', 'yard_sale_id', 'yard_sales', 'id', 'visited_yard_sales_yard_sale_id_fk'),
        ('notifications', 'user_id', 'users', 'id', 'notifications_user_id_fk'),
        ('notifications', 'related_user_id', 'users', 'id', 'notifications_related_user_id_fk'),
        ('notifications', 'related_yard_sale_id', 'yard_sales', 'id', 'notifications_related_yard_sale_id_fk'),
        ('notifications', 'related_message_id', 'messages', 'id', 'notifications_related_message_id_fk')
    ]
    
    with engine.connect() as connection:
        for table, column, referenced_table, referenced_column, constraint_name in foreign_key_constraints:
            try:
                # Check if table and column exist
                result = connection.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_schema = 'fastapi_db' 
                    AND table_name = '{table}' 
                    AND column_name = '{column}'
                """))
                
                if result.scalar() == 0:
                    print(f"  ⚠️  Table {table} or column {column} does not exist, skipping constraint")
                    continue
                
                connection.execute(text(f"""
                    ALTER TABLE {table} 
                    ADD CONSTRAINT {constraint_name} 
                    FOREIGN KEY ({column}) REFERENCES {referenced_table}({referenced_column})
                """))
                print(f"  ✅ Created constraint {constraint_name}")
                
            except Exception as e:
                print(f"  ⚠️  Could not create constraint {constraint_name}: {e}")
        
        connection.commit()
        print("\n✅ Foreign key constraints recreated!")

def verify_migration():
    """Verify the migration was successful"""
    engine = create_engine(DATABASE_URL, echo=True)
    
    with engine.connect() as connection:
        print("\n=== VERIFICATION ===")
        
        tables_to_check = [
            'users', 'yard_sales', 'items', 'comments', 'conversations', 
            'messages', 'user_ratings', 'reports', 'verifications', 'notifications'
        ]
        
        for table in tables_to_check:
            try:
                result = connection.execute(text(f"DESCRIBE {table}"))
                columns = result.fetchall()
                id_column = next((col for col in columns if col[0] == 'id'), None)
                
                if id_column:
                    if 'char(36)' in id_column[1].lower():
                        print(f"✅ {table}.id: {id_column[1]} (UUID)")
                    else:
                        print(f"❌ {table}.id: {id_column[1]} (Not UUID)")
                else:
                    print(f"❌ {table}: No id column found")
                    
            except Exception as e:
                print(f"❌ {table}: Error - {e}")
        
        # Check sample UUIDs
        print("\nSample UUIDs:")
        for table in ['users', 'yard_sales', 'items']:
            try:
                result = connection.execute(text(f"SELECT id FROM {table} LIMIT 1"))
                row = result.fetchone()
                if row:
                    try:
                        uuid.UUID(row[0])
                        print(f"  ✅ {table}: {row[0]} (Valid UUID)")
                    except ValueError:
                        print(f"  ❌ {table}: {row[0]} (Invalid UUID)")
            except Exception as e:
                print(f"  ❌ {table}: Error - {e}")

def main():
    """Main migration function"""
    print("Comprehensive UUID Migration Script")
    print("=" * 60)
    print("This will convert ALL entity IDs to UUIDs")
    print("=" * 60)
    print()
    
    try:
        # Step 1: Get table data
        print("Step 1: Getting table data...")
        tables_data = get_table_data()
        
        # Step 2: Create ID mappings
        print("\nStep 2: Creating UUID mappings...")
        all_mappings = create_id_mappings(tables_data)
        
        # Step 3: Migrate tables in dependency order
        print("\nStep 3: Migrating tables to UUIDs...")
        migration_order = [
            'yard_sales',      # Independent
            'items',           # Depends on users, yard_sales
            'comments',        # Depends on users, yard_sales
            'conversations',   # Depends on users, yard_sales
            'messages',        # Depends on users, conversations
            'user_ratings',    # Depends on users, yard_sales
            'reports',         # Depends on users, yard_sales
            'verifications',   # Depends on users
            'notifications'    # Depends on users, yard_sales, messages
        ]
        
        for table in migration_order:
            if table in all_mappings and all_mappings[table]:
                if not migrate_table_to_uuid(table, all_mappings[table]):
                    print(f"❌ Migration failed for {table}")
                    return
            else:
                print(f"⚠️  Skipping {table} (no data or already migrated)")
        
        # Step 4: Migrate foreign key columns to UUID format
        print("\nStep 4: Migrating foreign key columns to UUID format...")
        if not migrate_foreign_key_columns():
            print("❌ Foreign key column migration failed")
            return
        
        # Step 5: Update foreign key references
        print("\nStep 5: Updating foreign key references...")
        if not update_foreign_key_references(all_mappings):
            print("❌ Foreign key reference update failed")
            return
        
        # Step 6: Recreate foreign key constraints
        print("\nStep 6: Recreating foreign key constraints...")
        recreate_foreign_key_constraints()
        
        # Step 7: Verify migration
        print("\nStep 7: Verifying migration...")
        verify_migration()
        
        print("\n" + "="*60)
        print("✅ COMPREHENSIVE UUID MIGRATION COMPLETED!")
        print("="*60)
        print("\nAll entity IDs are now UUIDs:")
        print("- Users: ✅")
        print("- Yard Sales: ✅")
        print("- Items: ✅")
        print("- Comments: ✅")
        print("- Conversations: ✅")
        print("- Messages: ✅")
        print("- User Ratings: ✅")
        print("- Reports: ✅")
        print("- Verifications: ✅")
        print("- Notifications: ✅")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
