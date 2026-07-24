"""OCDS source discovery via its official resource/landing page."""

from __future__ import annotations

from ..models import Asset, Source
from .landing_page import LandingPageAdapter


class OCDSAdapter(LandingPageAdapter):
    def discover(self, source: Source, context):
        assets, evidence = super().discover(source, context)
        json_assets = [
            asset for asset in assets
            if "json" in asset.expected_formats or asset.requested_url.lower().split("?", 1)[0].endswith((".json", ".zip"))
        ]
        evidence["adapter"] = "ocds"
        evidence["ocds_candidates_before_filter"] = len(assets)
        return json_assets or assets, evidence
