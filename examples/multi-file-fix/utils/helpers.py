"""
Helper functions for data processing and formatting.
"""


def calculate_average(numbers):
    """
    Calculate the average of a list of numbers.

    Args:
        numbers (list): List of numbers

    Returns:
        float: The average value

    Bug: This function has a division by zero bug when the list is empty!
    """
    total = sum(numbers)
    # BUG: No check for empty list - will cause ZeroDivisionError
    return total / len(numbers)


def format_currency(amount):
    """
    Format a number as currency (USD).

    Args:
        amount (float): The amount to format

    Returns:
        str: Formatted currency string

    Bug: Missing dollar sign in return statement!
    """
    # BUG: Missing '$' prefix
    return f"{amount:,.2f}"  # Should be f"${amount:,.2f}"


def calculate_total(items, key='amount'):
    """
    Calculate total from a list of dictionaries.

    Args:
        items (list): List of dictionaries
        key (str): Key to sum

    Returns:
        float: Total sum
    """
    return sum(item.get(key, 0) for item in items)
