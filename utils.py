"""
Utility functions for Inventory and Sales Analytics System.
"""

def format_inr(number):
    """
    Format a number into Indian Rupee currency format (e.g. ₹1,25,000.00).
    Follows the Indian numbering system (Lakhs and Crores).
    """
    if number is None:
        return "₹0.00"
    try:
        val = float(number)
    except (ValueError, TypeError):
        return f"₹{number}"
    
    is_neg = val < 0
    val = abs(val)
    formatted = f"{val:.2f}"
    parts = formatted.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) > 3:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        grouped = []
        while len(remaining) > 2:
            grouped.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            grouped.insert(0, remaining)
        integer_part = ",".join(grouped) + "," + last_three

    prefix = "-₹" if is_neg else "₹"
    return f"{prefix}{integer_part}.{decimal_part}"
