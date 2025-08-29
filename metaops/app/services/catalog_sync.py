from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Product


class CatalogSyncService:
	def __init__(self, session: Session) -> None:
		self.session = session

	def sync_from_inventory(self, inventory_rows: List[Dict]) -> Dict[str, int]:
		created = 0
		updated = 0
		for row in inventory_rows:
			sku = row.get("sku")
			stmt = select(Product).where(Product.sku == sku)
			existing = self.session.execute(stmt).scalar_one_or_none()
			if existing:
				existing.name = row.get("name")
				existing.description = row.get("description")
				existing.price = row.get("price")
				existing.stock = row.get("stock")
				existing.image_url = row.get("image_url")
				existing.category = row.get("category")
				updated += 1
			else:
				prod = Product(
					sku=row.get("sku"),
					name=row.get("name"),
					description=row.get("description"),
					price=row.get("price"),
					stock=row.get("stock"),
					image_url=row.get("image_url"),
					category=row.get("category"),
				)
				self.session.add(prod)
				created += 1
		return {"processed": len(inventory_rows), "created": created, "updated": updated, "errors": 0}