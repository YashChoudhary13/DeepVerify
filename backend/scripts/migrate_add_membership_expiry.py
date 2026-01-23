"""
Migration script to add membership_expiry column to users table
"""
import os
import sys

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

def migrate():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='membership_expiry'
        """))
        
        if result.fetchone():
            print("✓ Column 'membership_expiry' already exists")
            return
        
        # Add the column
        print("Adding 'membership_expiry' column to users table...")
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN membership_expiry TIMESTAMP NULL
        """))
        conn.commit()
        print("✓ Migration completed successfully")

if __name__ == "__main__":
    migrate()
