"""Direct public file adapter."""

from __future__ import annotations

from ..discovery import filename_from_url, infer_financial_year
from ..models import Asset, Source
from ..storage import safe_filename
from .base import AdapterContext, BaseAdapter


class DirectFileAdapter(BaseAdapter):
    def discover(self, source: Source, context: AdapterContext) -> tuple[list[Asset], dict]:
        if not source.resource_url:
            return [], {"error": "registry has no resource_url", "candidates": [], "rejected": []}
        filename = source.storage.get("canonical_filename") or filename_from_url(
            source.resource_url, source.id
        )
        period = infer_financial_year(f"{source.title} {source.resource_url} {source.research.get('time_coverage', '')}")
        asset = Asset(
            source_id=source.id,
            asset_instance_id=f"{source.id}:{period or 'undated'}:{safe_filename(filename).rsplit('.', 1)[0]}",
            requested_url=source.resource_url,
            title=source.title,
            expected_formats=source.formats,
            financial_year=period,
            filename_hint=filename,
            discovery_url=source.landing_url,
            metadata={"adapter": "direct_file"},
        )
        return [asset], {"landing_url": source.landing_url, "candidates": [asset.requested_url], "rejected": []}
