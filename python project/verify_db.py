import os
import sys
from sqlalchemy import inspect
from app import create_app
from extensions import db
from models import Product, Sale

def verify_database():
    print("=" * 60)
    print("PHASE 2: DATABASE VERIFICATION TEST")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        # 1. Verify Database File and Location
        db_path = os.path.join(app.instance_path, 'inventory.db')
        print(f"\n[1] Checking Database Location...")
        print(f"    Expected DB Path: {db_path}")
        print(f"    Instance Folder Exists: {os.path.exists(app.instance_path)}")
        print(f"    inventory.db Exists: {os.path.exists(db_path)}")
        assert os.path.exists(db_path), "Database file inventory.db was not found in instance folder!"
        print("    -> PASS: Database file is created in instance folder.")

        # 2. Confirm Both Tables Exist
        print(f"\n[2] Checking Tables in Database...")
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        print(f"    Discovered Tables: {table_names}")
        assert 'products' in table_names, "Table 'products' does not exist!"
        assert 'sales' in table_names, "Table 'sales' does not exist!"
        print("    -> PASS: Both 'products' and 'sales' tables exist.")

        # Inspect columns of products
        prod_cols = [col['name'] for col in inspector.get_columns('products')]
        print(f"    'products' Columns: {prod_cols}")
        for req_col in ['id', 'name', 'category', 'price', 'stock', 'description']:
            assert req_col in prod_cols, f"Column {req_col} missing in products table!"

        # Inspect columns of sales
        sale_cols = [col['name'] for col in inspector.get_columns('sales')]
        print(f"    'sales' Columns: {sale_cols}")
        for req_col in ['id', 'product_id', 'quantity', 'total_amount', 'sale_date']:
            assert req_col in sale_cols, f"Column {req_col} missing in sales table!"

        # 3. Test Sample Product Insertion & Retrieval
        print(f"\n[3] Testing Product Insertion & Retrieval...")
        test_product_name = "Sample Mechanical Keyboard"
        # Check if already exists from prior runs to keep test idempotent
        product = Product.query.filter_by(name=test_product_name).first()
        if not product:
            product = Product(
                name=test_product_name,
                category="Accessories",
                price=89.99,
                stock=25,
                description="High-performance mechanical keyboard for verification."
            )
            db.session.add(product)
            db.session.commit()
            print(f"    Inserted new product (ID: {product.id})")
        else:
            print(f"    Found existing test product (ID: {product.id})")

        # Retrieve and verify product attributes
        retrieved_product = Product.query.filter_by(name=test_product_name).first()
        assert retrieved_product is not None, "Failed to retrieve sample product!"
        assert retrieved_product.price == 89.99
        assert retrieved_product.stock == 25
        assert retrieved_product.category == "Accessories"
        print(f"    Retrieved: {retrieved_product}")
        print("    -> PASS: Product insertion and retrieval verified.")

        # 4. Test Product-Sales Relationship
        print(f"\n[4] Testing One-to-Many Product-Sales Relationship...")
        sample_sale = Sale(
            product_id=retrieved_product.id,
            quantity=2,
            total_amount=179.98
        )
        db.session.add(sample_sale)
        db.session.commit()
        print(f"    Created sale record (ID: {sample_sale.id}) for Product ID {retrieved_product.id}")

        # Verification from Product -> Sales (One-to-Many)
        assert len(retrieved_product.sales) > 0, "Product.sales relationship failed to load linked sales!"
        assert sample_sale in retrieved_product.sales, "Sale record missing from Product.sales collection!"
        print(f"    Verified Product.sales: contains {len(retrieved_product.sales)} sale record(s)")

        # Verification from Sale -> Product (Many-to-One back-reference)
        retrieved_sale = db.session.get(Sale, sample_sale.id)
        assert retrieved_sale.product is not None, "Sale.product back-reference is None!"
        assert retrieved_sale.product.id == retrieved_product.id, "Sale.product does not match original product!"
        print(f"    Verified Sale.product: links back to '{retrieved_sale.product.name}'")
        print("    -> PASS: One-to-Many relationship and back_populates verified.")

    print("\n" + "=" * 60)
    print("ALL PHASE 2 DATABASE VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    verify_database()
