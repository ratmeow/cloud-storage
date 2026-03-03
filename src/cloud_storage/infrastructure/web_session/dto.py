import datetime
from dataclasses import dataclass


@dataclass
class SessionDTO:
    id: str
    user_id: str
    expired_ts: datetime.datetime
