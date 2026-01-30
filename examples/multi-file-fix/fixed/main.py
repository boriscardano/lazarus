#!/usr/bin/env python3
"""
Sales Report Generator

This script uses helper functions from the utils package.
This is the FIXED version - the bugs are fixed in the utils/helpers.py file.
"""

from utils import calculate_average, calculate_total, format_currency


def generate_sales_report(sales_data):
    """Generate a comprehensive sales report."""
    print("=" * 50)
    print("SALES REPORT")
    print("=" * 50)

    # Calculate total sales
    total = calculate_total(sales_data, key='amount')
    print(f"\nTotal Sales: {format_currency(total)}")

    # Calculate average sale
    amounts = [sale['amount'] for sale in sales_data]
    average = calculate_average(amounts)
    print(f"Average Sale: {format_currency(average)}")

    # Show number of transactions
    print(f"Number of Transactions: {len(sales_data)}")

    # Show breakdown by product
    print("\nSales by Product:")
    products = {}
    for sale in sales_data:
        product = sale['product']
        if product not in products:
            products[product] = []
        products[product].append(sale['amount'])

    for product, amounts in products.items():
        product_total = sum(amounts)
        product_avg = calculate_average(amounts)
        print(f"  {product}:")
        print(f"    Total: {format_currency(product_total)}")
        print(f"    Average: {format_currency(product_avg)}")
        print(f"    Count: {len(amounts)}")


def main():
    # Sample sales data
    sales_data = [
        {'id': 1, 'product': 'Widget A', 'amount': 150.00},
        {'id': 2, 'product': 'Widget B', 'amount': 75.50},
        {'id': 3, 'product': 'Widget A', 'amount': 200.00},
        {'id': 4, 'product': 'Widget C', 'amount': 125.75},
        {'id': 5, 'product': 'Widget B', 'amount': 90.00},
    ]

    print("Sales Report Generator v1.0\n")
    generate_sales_report(sales_data)

    # This will now work - empty list is handled gracefully
    print("\n" + "=" * 50)
    print("TESTING EDGE CASE")
    print("=" * 50)

    # Simulate a product with no sales (empty list)
    print("\nCalculating average for empty sales list...")
    try:
        empty_average = calculate_average([])  # This now works!
        print(f"Average: {format_currency(empty_average)}")
    except ZeroDivisionError as e:
        print(f"ERROR: {e}")
        raise

    print("\n✓ Report generated successfully!")


if __name__ == '__main__':
    main()
