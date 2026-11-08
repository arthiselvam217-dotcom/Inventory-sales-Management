from datetime import datetime, timezone
from flask import render_template, request, redirect, url_for, flash
from extensions import db
from models import Product, Sale
from utils import format_inr
from . import sales_bp

@sales_bp.route('/', methods=['GET'])
def index():
    """Display sales management page with product dropdown and sales history."""
    products = Product.query.order_by(Product.name.asc()).all()
    sales = Sale.query.order_by(Sale.sale_date.desc(), Sale.id.desc()).all()
    
    # Calculate simple aggregate metrics for summary display
    total_revenue = sum(s.total_amount for s in sales)
    total_units_sold = sum(s.quantity for s in sales)

    return render_template(
        'sales.html',
        products=products,
        sales=sales,
        total_revenue=total_revenue,
        total_units_sold=total_units_sold
    )

@sales_bp.route('/record', methods=['POST'])
def record_sale():
    """Record a sale transaction with validation and atomic stock deduction."""
    product_id_str = request.form.get('product_id', '').strip()
    quantity_str = request.form.get('quantity', '').strip()

    # 1. Validate Product selection
    if not product_id_str:
        flash("Please select a product from the list.", "danger")
        return redirect(url_for('sales.index'))

    try:
        product_id = int(product_id_str)
    except (ValueError, TypeError):
        flash("Invalid product selection.", "danger")
        return redirect(url_for('sales.index'))

    product = db.session.get(Product, product_id)
    if not product:
        flash("Selected product does not exist.", "danger")
        return redirect(url_for('sales.index'))

    # 2. Validate Quantity
    if not quantity_str:
        flash("Please enter the quantity sold.", "danger")
        return redirect(url_for('sales.index'))

    try:
        quantity = int(quantity_str)
    except (ValueError, TypeError):
        flash("Quantity must be a valid whole number.", "danger")
        return redirect(url_for('sales.index'))

    # Prevent zero or negative quantities
    if quantity <= 0:
        flash("Sale quantity must be greater than zero.", "danger")
        return redirect(url_for('sales.index'))

    # Prevent sales exceeding available stock
    if quantity > product.stock:
        flash(
            f"Insufficient stock! Requested {quantity} unit(s), but only {product.stock} available for '{product.name}'.",
            "danger"
        )
        return redirect(url_for('sales.index'))

    # 3. Execute atomic transaction (Create Sale + Deduct Stock)
    try:
        total_amount = round(product.price * quantity, 2)
        
        # Decrement stock
        product.stock -= quantity

        # Create new sale record linked to product
        sale = Sale(
            product_id=product.id,
            quantity=quantity,
            total_amount=total_amount,
            sale_date=datetime.now(timezone.utc)
        )
        db.session.add(sale)
        db.session.commit()

        flash(
            f"Sale recorded successfully! Sold {quantity} × '{product.name}' for {format_inr(total_amount)}. Remaining stock: {product.stock}.",
            "success"
        )
    except Exception as e:
        db.session.rollback()
        flash(f"Database error while recording sale: {str(e)}", "danger")

    return redirect(url_for('sales.index'))
