"""Independent tenant-scoped storage namespace owner."""

from .registry import StorageRegistry, StorageRegistryError, StorageResult

__all__ = ["StorageRegistry", "StorageRegistryError", "StorageResult"]
