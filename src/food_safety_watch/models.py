from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class SafetyRecord:
    id: str
    source_id: str
    source_record_id: str
    authority: str
    authority_region: str
    action_type: str
    event_date: str
    origin_country: str
    producer_name: str
    producer_location: str
    product_code: str
    product_category: str
    product_name: str
    reasons: list[str]
    hazard_tags: list[str]
    source_url: str
    retrieved_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def stable_id(source_id: str, source_record_id: str) -> str:
    value = f"{source_id}:{source_record_id}".encode("utf-8")
    return sha256(value).hexdigest()
