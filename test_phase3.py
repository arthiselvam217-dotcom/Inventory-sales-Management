import os
import sys

# Ensure UTF-8 output encoding for Indian Rupee symbol on Windows consoles
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from app import app
from extensions import db
from models import Product, Sale

def run_tests():
    print("=" * 70)
    print("PHASE 3: COMPREHENSIVE PRODUCT & SALES MANAGEMENT TEST SUITE")
    print("=" * 70)

    client = app.test_client()

    with app.app_context():
        # Clean up any leftover test products from previous test runs
        test_names = ["Test Gaming Headset", "Test Gaming Headset Pro", "Temp Product For Deletion"]
        existing = Product.query.filter(Product.name.in_(test_names)).all()
        for p in existing:
            db.session.delete(p)
        db.session.commit()

        # ---------------------------------------------------------
        # TEST 1: Add a sample product through the client/browser
        # ---------------------------------------------------------
        print("\n[TEST 1] Adding a sample product via POST /products/add...")
        res = client.post('/products/add', data={
            'name': 'Test Gaming Headset',
            'category': 'Audio',
            'price': '79.99',
            'stock': '15',
            'description': 'High fidelity spatial audio headset'
        }, follow_redirects=True)
        assert res.status_code == 200, f"Expected 200 after redirect, got {res.status_code}"
        
        prod = Product.query.filter_by(name='Test Gaming Headset').first()
        assert prod is not None, "Product was not inserted into database!"
        assert prod.price == 79.99, f"Expected price 79.99, got {prod.price}"
        assert prod.stock == 15, f"Expected stock 15, got {prod.stock}"
        print(f" -> PASS: Product '{prod.name}' added with ID={prod.id}, price=₹{prod.price}, stock={prod.stock}")

        # ---------------------------------------------------------
        # TEST 2 & 3: Edit details & verify updated information
        # ---------------------------------------------------------
        print("\n[TEST 2 & 3] Editing product details via POST /products/edit/<id>...")
        res = client.post(f'/products/edit/{prod.id}', data={
            'name': 'Test Gaming Headset Pro',
            'category': 'Pro Audio',
            'price': '89.99',
            'stock': '12',
            'description': 'Upgraded drivers with wireless dongle'
        }, follow_redirects=True)
        assert res.status_code == 200

        # Verify in database
        updated_prod = db.session.get(Product, prod.id)
        assert updated_prod.name == 'Test Gaming Headset Pro', f"Name not updated: {updated_prod.name}"
        assert updated_prod.price == 89.99, f"Price not updated: {updated_prod.price}"
        assert updated_prod.stock == 12, f"Stock not updated: {updated_prod.stock}"
        assert updated_prod.category == 'Pro Audio'

        # Verify on Products page HTML
        page_html = res.get_data(as_text=True)
        assert 'Test Gaming Headset Pro' in page_html, "Updated product name not visible on page!"
        assert '₹89.99' in page_html, "Updated price not visible on page!"
        assert '12 in stock' in page_html, "Updated stock not visible on page!"
        print(f" -> PASS: Verified updated product: '{updated_prod.name}', Price=₹{updated_prod.price}, Stock={updated_prod.stock}")

        # ---------------------------------------------------------
        # TEST 4 & 5: Record a sale & verify total amount
        # ---------------------------------------------------------
        print("\n[TEST 4 & 5] Recording a sale of 3 units via POST /sales/record...")
        qty_to_sell = 3
        expected_total = round(updated_prod.price * qty_to_sell, 2)  # 89.99 * 3 = 269.97

        res = client.post('/sales/record', data={
            'product_id': str(updated_prod.id),
            'quantity': str(qty_to_sell)
        }, follow_redirects=True)
        assert res.status_code == 200

        # Retrieve newest sale record for this product
        newest_sale = Sale.query.filter_by(product_id=updated_prod.id).order_by(Sale.id.desc()).first()
        assert newest_sale is not None, "Sale record was not created!"
        assert newest_sale.quantity == 3, f"Expected quantity 3, got {newest_sale.quantity}"
        assert newest_sale.total_amount == expected_total, f"Expected total {expected_total}, got {newest_sale.total_amount}"
        print(f" -> PASS: Sale recorded: ID={newest_sale.id}, Qty={newest_sale.quantity}, Total=₹{newest_sale.total_amount:,.2f}")

        # ---------------------------------------------------------
        # TEST 6: Verify that stock decreases correctly
        # ---------------------------------------------------------
        print("\n[TEST 6] Verifying stock decrease in inventory...")
        db.session.refresh(updated_prod)
        expected_remaining_stock = 12 - 3  # 9
        assert updated_prod.stock == expected_remaining_stock, f"Expected stock {expected_remaining_stock}, got {updated_prod.stock}"
        print(f" -> PASS: Product stock decreased from 12 to {updated_prod.stock} successfully.")

        # ---------------------------------------------------------
        # TEST 7: Test that selling more than available stock is rejected
        # ---------------------------------------------------------
        print("\n[TEST 7] Testing invalid sale quantities (over-stock and negative)...")
        # Attempt 1: Sell 20 units when only 9 available
        res_overstock = client.post('/sales/record', data={
            'product_id': str(updated_prod.id),
            'quantity': '20'
        }, follow_redirects=True)
        html_overstock = res_overstock.get_data(as_text=True)
        assert 'Insufficient stock' in html_overstock, "Overstock sale was not rejected!"
        db.session.refresh(updated_prod)
        assert updated_prod.stock == 9, "Stock changed after rejected overstock sale!"

        # Attempt 2: Sell negative units
        res_neg = client.post('/sales/record', data={
            'product_id': str(updated_prod.id),
            'quantity': '-5'
        }, follow_redirects=True)
        html_neg = res_neg.get_data(as_text=True)
        assert 'greater than zero' in html_neg, "Negative sale quantity was not rejected!"

        # Attempt 3: Sell 0 units
        res_zero = client.post('/sales/record', data={
            'product_id': str(updated_prod.id),
            'quantity': '0'
        }, follow_redirects=True)
        html_zero = res_zero.get_data(as_text=True)
        assert 'greater than zero' in html_zero, "Zero sale quantity was not rejected!"

        print(" -> PASS: Over-stock, zero, and negative quantities properly rejected without altering stock.")

        # ---------------------------------------------------------
        # TEST 8: Verify the sales history
        # ---------------------------------------------------------
        print("\n[TEST 8] Verifying sales history display via GET /sales/...")
        res_sales = client.get('/sales/')
        assert res_sales.status_code == 200
        sales_html = res_sales.get_data(as_text=True)
        assert 'Test Gaming Headset Pro' in sales_html, "Product name missing in sales history!"
        assert '₹269.97' in sales_html, "Total amount missing in sales history!"
        assert f'#{newest_sale.id}' in sales_html, "Sale ID missing in sales history!"
        print(f" -> PASS: Sale #{newest_sale.id} verified in sales history table with correct amount and product.")

        # ---------------------------------------------------------
        # TEST 9: Test product deletion safely
        # ---------------------------------------------------------
        print("\n[TEST 9] Testing safe product deletion...")
        # Add temporary product
        temp_prod = Product(
            name='Temp Product For Deletion',
            category='Misc',
            price=19.99,
            stock=5,
            description='To be deleted'
        )
        db.session.add(temp_prod)
        db.session.commit()
        temp_id = temp_prod.id

        # Record a sale for temp product
        temp_sale = Sale(
            product_id=temp_id,
            quantity=1,
            total_amount=19.99
        )
        db.session.add(temp_sale)
        db.session.commit()
        temp_sale_id = temp_sale.id

        # Delete product
        del_res = client.post(f'/products/delete/{temp_id}', follow_redirects=True)
        assert del_res.status_code == 200

        # Confirm product is deleted
        deleted_check = db.session.get(Product, temp_id)
        assert deleted_check is None, "Product still exists after deletion!"

        # Confirm cascaded sale is removed or handled safely
        deleted_sale_check = db.session.get(Sale, temp_sale_id)
        assert deleted_sale_check is None, "Cascaded sale record was not deleted!"
        print(f" -> PASS: Product #{temp_id} and associated sales deleted safely.")

        # ---------------------------------------------------------
        # TEST 10: Product Search Option
        # ---------------------------------------------------------
        print("\n[TEST 10] Testing product search option...")
        # Search for 'Headset'
        search_res = client.get('/products/?q=Headset')
        assert search_res.status_code == 200
        search_html = search_res.get_data(as_text=True)
        assert 'Test Gaming Headset Pro' in search_html, "Search did not return matching product!"

        # Search for non-existent product
        search_empty = client.get('/products/?q=NonExistentZ99')
        assert search_empty.status_code == 200
        empty_html = search_empty.get_data(as_text=True)
        assert 'No products found matching "NonExistentZ99"' in empty_html
        print(" -> PASS: Product search filtering verified.")

        # ---------------------------------------------------------
        # TEST 11: Phase 1 & 2 Regression Verification
        # ---------------------------------------------------------
        print("\n[TEST 11] Verifying Phase 1 and Phase 2 regression...")
        home_res = client.get('/')
        assert home_res.status_code == 200
        assert 'Welcome to Inventory and Sales Analytics System' in home_res.get_data(as_text=True)

        dash_res = client.get('/dashboard')
        assert dash_res.status_code == 200
        assert 'Welcome to Inventory and Sales Analytics System' in dash_res.get_data(as_text=True)
        print(" -> PASS: Phase 1 home/dashboard welcome page intact and functional.")

    print("\n" + "=" * 70)
    print("ALL 11 PHASE 3 INTEGRATION & REGRESSION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == '__main__':
    run_tests()
