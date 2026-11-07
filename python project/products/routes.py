from flask import render_template, request, redirect, url_for, flash
from extensions import db
from models import Product
from . import products_bp

@products_bp.route('/', methods=['GET'])
def index():
    """Display product catalog with search support."""
    search_query = request.args.get('q', '').strip()
    if search_query:
        products = Product.query.filter(Product.name.ilike(f"%{search_query}%")).order_by(Product.name.asc()).all()
    else:
        products = Product.query.order_by(Product.id.desc()).all()
    
    return render_template('products.html', products=products, search_query=search_query)

@products_bp.route('/add', methods=['POST'])
def add():
    """Handle product creation with validation."""
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    price_str = request.form.get('price', '').strip()
    stock_str = request.form.get('stock', '').strip()
    description = request.form.get('description', '').strip()

    # Validation
    if not name:
        flash("Product name is required.", "danger")
        return redirect(url_for('products.index'))

    try:
        price = float(price_str)
        if price < 0:
            flash("Price cannot be negative.", "danger")
            return redirect(url_for('products.index'))
    except (ValueError, TypeError):
        flash("Invalid price format. Please enter a valid number.", "danger")
        return redirect(url_for('products.index'))

    try:
        stock = int(stock_str)
        if stock < 0:
            flash("Stock quantity cannot be negative.", "danger")
            return redirect(url_for('products.index'))
    except (ValueError, TypeError):
        flash("Invalid stock format. Please enter a whole integer.", "danger")
        return redirect(url_for('products.index'))

    try:
        new_product = Product(
            name=name,
            category=category if category else None,
            price=round(price, 2),
            stock=stock,
            description=description if description else None
        )
        db.session.add(new_product)
        db.session.commit()
        flash(f"Product '{name}' added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Database error adding product: {str(e)}", "danger")

    return redirect(url_for('products.index'))

@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit(product_id):
    """Handle product editing and updates."""
    product = db.session.get(Product, product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('products.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        price_str = request.form.get('price', '').strip()
        stock_str = request.form.get('stock', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash("Product name is required.", "danger")
            return render_template('edit_product.html', product=product)

        try:
            price = float(price_str)
            if price < 0:
                flash("Price cannot be negative.", "danger")
                return render_template('edit_product.html', product=product)
        except (ValueError, TypeError):
            flash("Invalid price format. Please enter a valid number.", "danger")
            return render_template('edit_product.html', product=product)

        try:
            stock = int(stock_str)
            if stock < 0:
                flash("Stock cannot be negative.", "danger")
                return render_template('edit_product.html', product=product)
        except (ValueError, TypeError):
            flash("Invalid stock format. Please enter a whole integer.", "danger")
            return render_template('edit_product.html', product=product)

        try:
            product.name = name
            product.category = category if category else None
            product.price = round(price, 2)
            product.stock = stock
            product.description = description if description else None
            db.session.commit()
            flash(f"Product '{name}' updated successfully!", "success")
            return redirect(url_for('products.index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Database error updating product: {str(e)}", "danger")

    return render_template('edit_product.html', product=product)

@products_bp.route('/delete/<int:product_id>', methods=['POST'])
def delete(product_id):
    """Safely delete a product."""
    product = db.session.get(Product, product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('products.index'))

    try:
        product_name = product.name
        db.session.delete(product)
        db.session.commit()
        flash(f"Product '{product_name}' deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Database error deleting product: {str(e)}", "danger")

    return redirect(url_for('products.index'))
