from extensions import db

class Product(db.Model):
    """
    Product Model representing inventory items.
    """
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # One-to-Many Relationship: One product can have multiple sales records
    sales = db.relationship('Sale', back_populates='product', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f"<Product id={self.id} name='{self.name}' price={self.price} stock={self.stock}>"
