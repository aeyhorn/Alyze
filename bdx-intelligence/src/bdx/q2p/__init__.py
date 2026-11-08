"""Quote-to-Promise (Q2P) – parallel inquiry evaluation.

Replaces serial multi-person clarification (material, capacity, pricing)
with a single inquiry case that fans out domain checks against SAP + shop floor.
"""
from __future__ import annotations

from bdx.q2p.service import evaluate_promise
from bdx.q2p.store import create_inquiry, get_inquiry, list_inquiries, update_inquiry

__all__ = [
    "evaluate_promise",
    "create_inquiry",
    "get_inquiry",
    "list_inquiries",
    "update_inquiry",
]
