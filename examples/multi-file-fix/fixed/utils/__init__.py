"""
Utility package for data processing.

Fixed version - imports calculate_total as well.
"""

from .helpers import calculate_average, calculate_total, format_currency

__all__ = ['calculate_average', 'format_currency', 'calculate_total']
