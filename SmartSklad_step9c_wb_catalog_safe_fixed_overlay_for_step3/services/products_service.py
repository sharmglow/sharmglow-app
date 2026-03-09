"""services/products_service.py"""

class ProductsService:
    def __init__(self, db):
        self.db = db

    def get_all(self, search=""):
        return self.db.get_products(search)

    def get_by_article(self, art):
        return self.db.get_product(art)

    def get_by_id(self, pid):
        return self.db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()

    def get_stock(self, art):
        return self.db.get_stock(art)

    def get_categories(self):
        return self.db.get_categories()

    def create(self, art, name, cat, unit, min_stock, bc_wb, bc_ozon, supplier, note):
        return self.db.add_product(art, name, cat, unit, min_stock, bc_wb, bc_ozon, supplier, note)

    def update(self, pid, art, name, cat, unit, min_stock, bc_wb, bc_ozon, supplier, note):
        return self.db.update_product(pid, art, name, cat, unit, min_stock, bc_wb, bc_ozon, supplier, note)

    def delete(self, pid):
        return self.db.delete_product(pid)
