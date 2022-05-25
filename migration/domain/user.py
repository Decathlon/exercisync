from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from bson import ObjectId

from migration.domain.connection import Connection


@dataclass
class User:
    hub_id: ObjectId
    connected_services: List[Connection] = field(default_factory=list)
    member_id: str | None = None
