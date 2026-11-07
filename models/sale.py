from datetime import datetime, timezone
from extensions import db

class Sale(db.Model):
    """
    Sale Model representing sales transactions associated with products.
    """
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Many-to-One Relationship: Each sale record points back to a single Product
    product = db.relationship('Product', back_populates='sales')

    def __repr__(self):
        return f"<Sale id={self.id} product_id={self.product_id} quantity={self.quantity} total_amount={self.total_amount}>"
