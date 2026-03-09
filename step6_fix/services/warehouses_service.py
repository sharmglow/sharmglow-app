"""services/warehouses_service.py"""

class WarehousesService:
    def __init__(self, db):
        self.db = db

    def get_all(self):
        return self.db.get_warehouses()

    def get_by_id(self, wid):
        return self.db.conn.execute("SELECT * FROM warehouses WHERE id=?", (wid,)).fetchone()

    def create(self, code, name, wtype, note=""):
        return self.db.add_warehouse(code, name, wtype, note)

    def update(self, wid, code, name, wtype, note):
        return self.db.update_warehouse(wid, code, name, wtype, note)

    def delete(self, wid):
        return self.db.delete_warehouse(wid)
