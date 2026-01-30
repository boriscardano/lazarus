#!/usr/bin/env python3
"""
Data Fetcher Script - Uses the API module to fetch and display user data.

This is the FIXED version that properly uses API v2.0 with the new signature.
"""

import json

from api_module import get_user_data, list_users


def display_user(user_id):
    """Fetch and display a single user's data."""
    print(f"\nFetching user {user_id}...")

    # Fixed: Now properly includes the include_metadata parameter
    # We're explicitly passing False to match the old behavior
    user = get_user_data(user_id, include_metadata=False)

    print(f"User ID: {user['id']}")
    print(f"Name: {user['name']}")
    print(f"Email: {user['email']}")
    print(f"Status: {user['status']}")

    # Try to access metadata if it exists
    if 'metadata' in user:
        print("\nMetadata:")
        print(json.dumps(user['metadata'], indent=2))


def main():
    print("User Data Fetcher v1.0")
    print("=" * 40)

    # Display individual users
    display_user(42)
    display_user(123)

    # List all users
    print("\n\nFetching user list...")
    users = list_users(5)
    print(f"Found {len(users)} users")

    for user in users:
        print(f"  - {user['name']} ({user['email']})")

    print("\n✓ Data fetch completed successfully!")


if __name__ == '__main__':
    main()
