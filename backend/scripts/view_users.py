"""
View all users in the database
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app import models

def view_users():
    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        
        if not users:
            print("No users found in database")
            return
        
        print(f"\n{'='*80}")
        print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Membership':<12} {'Active':<8}")
        print(f"{'='*80}")
        
        for user in users:
            print(f"{user.id:<5} {user.username:<20} {user.email:<30} {user.membership_status:<12} {user.is_active}")
            if hasattr(user, 'membership_expiry') and user.membership_expiry:
                print(f"      Expires: {user.membership_expiry}")
        
        print(f"{'='*80}")
        print(f"Total users: {len(users)}\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    view_users()
