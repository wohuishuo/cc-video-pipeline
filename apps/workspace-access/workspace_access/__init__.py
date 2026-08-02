"""Workspace identity and least-privilege access policy owner."""

from .registry import AccessRegistry, AccessResult, RegistryError

__all__ = ["AccessRegistry", "AccessResult", "RegistryError"]
