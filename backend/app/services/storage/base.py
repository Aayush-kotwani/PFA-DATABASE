"""Abstract base interface for file storage backends."""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Contract for storing, deleting, and resolving URLs for uploaded media."""

    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Persist raw bytes under `key` and return the stored key."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the object stored at `key` if it exists."""

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Return a reachable URL for accessing the object stored at `key`."""
