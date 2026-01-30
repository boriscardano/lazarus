#!/usr/bin/env python3
"""
Data Fetcher Script - Uses the API module to fetch and display user data.

This script was written for version 1.0 of the API module and breaks with version 2.0
because the function signature changed.
"""

import json

from api_module import get_user_data, list_users


def display_user(user_id):
    """Fetch and display a single user's data."""
    print(f"\nFetching user {user_id}...")

    # BUG: This call is missing the new required 'include_metadata' parameter
    # In API v2.0, this function signature changed
    user = get_user_data(user_id)  # Missing: include_metadata parameter

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
