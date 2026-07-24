"""Socrata metadata/count discovery and full official CSV export."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from ..models import Asset, Source
from .base import AdapterContext, BaseAdapter


class SocrataAdapter(BaseAdapter):
    def discover(self, source: Source, context: AdapterContext) -> tuple[list[Asset], dict]:
        dataset_id = source.access.get("dataset_id")
        if not dataset_id:
            match = re.search(r"/([a-z0-9]{4}-[a-z0-9]{4})(?:$|[/?])", source.landing_url, re.I)
            if not match:
                raise ValueError("Socrata dataset ID not found")
            dataset_id = match.group(1)
        parsed = urlparse(source.landing_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        metadata_url = f"{origin}/api/views/{dataset_id}"
        count_url = f"{origin}/resource/{dataset_id}.json?$select=count(*)"
        metadata_response = context.http.get_bytes(metadata_url)
        count_response = context.http.get_bytes(count_url)
        metadata = json.loads(metadata_response.body or b"{}")
        count_payload = json.loads(count_response.body or b"[]")
        count = int(count_payload[0].get("count", 0)) if count_payload else 0
        export_url = f"{origin}/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD"
        asset = Asset(
            source_id=source.id,
            asset_instance_id=f"{source.id}:all:{dataset_id}",
            requested_url=export_url,
            title=metadata.get("name") or source.title,
            expected_formats=["csv"],
            filename_hint=f"{dataset_id}.csv",
            discovery_url=metadata_url,
            metadata={"adapter": "socrata", "dataset_id": dataset_id, "estimated_records": count},
        )
        return [asset], {
            "metadata_url": metadata_url,
            "count_url": count_url,
            "estimated_records": count,
            "metadata": metadata,
            "candidates": [export_url],
            "rejected": [],
        }
