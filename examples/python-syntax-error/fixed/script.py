#!/usr/bin/env python3
"""
Data Processing Script - Analyzes sales data and generates a report.

This is the FIXED version with the syntax error corrected.
"""

import json
from datetime import datetime


def calculate_total_sales(sales_data):  # Fixed: Added missing colon
    """Calculate the total sales from the data."""
    total = 0
    for sale in sales_data:
        total += sale.get('amount', 0)
    return total


def generate_report(sales_data):
    """Generate a sales report."""
    total = calculate_total_sales(sales_data)
    average = total / len(sales_data) if sales_data else 0

    report = {
        'timestamp': datetime.now().isoformat(),
        'total_sales': total,
        'average_sale': average,
        'num_transactions': len(sales_data)
    }

    return report


def main():
    # Sample sales data
    sales_data = [
        {'id': 1, 'amount': 150.00, 'product': 'Widget A'},
        {'id': 2, 'amount': 75.50, 'product': 'Widget B'},
        {'id': 3, 'amount': 200.00, 'product': 'Widget C'},
        {'id': 4, 'amount': 125.75, 'product': 'Widget A'},
        {'id': 5, 'amount': 90.00, 'product': 'Widget D'},
    ]

    print("Processing sales data...")
    report = generate_report(sales_data)

    print("\n=== Sales Report ===")
    print(json.dumps(report, indent=2))
    print("\nReport generated successfully!")


if __name__ == '__main__':
    main()
