from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    OWNER = "OWNER"
    CEO = "CEO"
    DEVELOPER = "DEVELOPER"
    ADMIN = "ADMIN"


@dataclass(frozen=True)
class AuthUser:
    email: str
    firebase_uid: str
    role: Role
    user_id: str
