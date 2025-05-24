#!/usr/bin/env python3
"""
Script to create admin user for NPC Tunisia Para Athletics application
Usage: python create_admin.py
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash
from database.db_manager import get_db_connection, execute_query, execute_one
from config import Config
from dotenv import load_dotenv

load_dotenv()


def create_admin_user(username='admin', password='admin2025'):
    """Create admin user with specified credentials"""

    try:
        # Check if user already exists
        existing_user = execute_one(
            "SELECT id FROM users WHERE username = %s",
            (username,)
        )

        if existing_user:
            print(f"❌ User '{username}' already exists!")
            response = input("Do you want to update the password? (y/n): ")

            if response.lower() == 'y':
                # Update existing user's password
                password_hash = generate_password_hash(password)
                execute_query(
                    "UPDATE users SET password_hash = %s WHERE username = %s",
                    (password_hash, username)
                )
                print(f"✅ Password updated successfully for user '{username}'")
            else:
                print("Operation cancelled.")
                return
        else:
            # Create new user
            password_hash = generate_password_hash(password)
            execute_query(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash)
            )
            print(f"✅ Admin user created successfully!")
            print(f"   Username: {username}")
            print(f"   Password: {password}")

        print(f"\n📌 You can now login at: http://localhost:5000/admin")

    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database 'npc_tunisia_db' exists")
        print("3. .env file is properly configured")


def main():
    print("=" * 50)
    print("NPC Tunisia Para Athletics - Admin User Setup")
    print("=" * 50)

    # Check if custom credentials are desired
    use_custom = input("\nUse custom credentials? (y/n) [default: n]: ").lower()

    if use_custom == 'y':
        username = input("Enter admin username [default: admin]: ").strip() or 'admin'
        password = input("Enter admin password [default: admin2025]: ").strip() or 'admin2025'

        if len(password) < 8:
            print("❌ Password must be at least 8 characters long!")
            return

        create_admin_user(username, password)
    else:
        # Use default credentials from .env or fallback
        username = Config.ADMIN_USERNAME if hasattr(Config, 'ADMIN_USERNAME') else 'admin'
        password = Config.ADMIN_PASSWORD if hasattr(Config, 'ADMIN_PASSWORD') else 'admin2025'
        create_admin_user(username, password)


if __name__ == "__main__":
    main()