"""
Simulated API Module - Represents a third-party library that changed its API.

Version 2.0 introduced breaking changes:
- get_user_data() now requires 'include_metadata' parameter
- The function signature changed from (user_id) to (user_id, include_metadata=False)
"""


def get_user_data(user_id, include_metadata=False):
    """
    Fetch user data from the API.

    Args:
        user_id (int): The user ID to fetch
        include_metadata (bool): Whether to include metadata in response

    Returns:
        dict: User data with optional metadata

    Note: Version 2.0 - This parameter is now required!
    Previously this function only took user_id as a parameter.
    """
    # Simulate API response
    user_data = {
        'id': user_id,
        'name': f'User {user_id}',
        'email': f'user{user_id}@example.com',
        'status': 'active'
    }

    if include_metadata:
        user_data['metadata'] = {
            'created_at': '2024-01-01',
            'last_login': '2024-12-15',
            'account_type': 'premium'
        }

    return user_data


def list_users(limit=10):
    """
    List all users with pagination.

    Args:
        limit (int): Maximum number of users to return

    Returns:
        list: List of user dictionaries
    """
    return [get_user_data(i, include_metadata=False) for i in range(1, limit + 1)]
