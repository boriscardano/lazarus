"""
Helper functions for data processing and formatting.

This is the FIXED version with both bugs corrected.
"""


def calculate_average(numbers):
    """
    Calculate the average of a list of numbers.

    Args:
        numbers (list): List of numbers

    Returns:
        float: The average value

    Fixed: Added check for empty list to prevent ZeroDivisionError
    """
    if not numbers:  # Fixed: Check for empty list
        return 0.0
    total = sum(numbers)
    return total / len(numbers)


def format_currency(amount):
    """
    Format a number as currency (USD).

    Args:
        amount (float): The amount to format

    Returns:
        str: Formatted currency string

    Fixed: Added dollar sign prefix
    """
    return f"${amount:,.2f}"  # Fixed: Added '$' prefix


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
