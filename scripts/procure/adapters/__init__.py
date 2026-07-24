"""Adapter registry."""

from .base import AdapterContext, BaseAdapter
from .browser_discovery import BrowserDiscoveryAdapter
from .ckan import CKANAdapter
from .direct_file import DirectFileAdapter
from .landing_page import LandingPageAdapter
from .manual import ManualAdapter
from .ocds import OCDSAdapter
from .socrata import SocrataAdapter

__all__ = [
    "AdapterContext", "BaseAdapter", "BrowserDiscoveryAdapter", "CKANAdapter",
    "DirectFileAdapter", "LandingPageAdapter", "ManualAdapter", "OCDSAdapter",
    "SocrataAdapter",
]
