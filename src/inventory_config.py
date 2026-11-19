
"""Configuration management for the inventory module."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class InventoryConfig:
    """Environment-driven settings for inventory storage and warehouse sync."""

    db_path: str = os.getenv("INVENTORY_DB_PATH", "/var/data/warehouse/inventory.db")
    backup_path: str = os.getenv("INVENTORY_BACKUP_PATH", "/var/data/warehouse/backup/")
    low_stock_threshold: int = int(os.getenv("INVENTORY_LOW_STOCK_THRESHOLD", "10"))
    warehouse_api_key: str = os.getenv("WAREHOUSE_API_KEY", "")
    warehouse_api_secret: str = os.getenv("WAREHOUSE_API_SECRET", "")
    warehouse_url: str = os.getenv(
        "WAREHOUSE_API_URL", "http://warehouse-internal.company.local/api/v1"
    )