import dataclasses

from auth import Authenticator
from database import Database


@dataclasses.dataclass
class Globals:
    backup_path: str = None
    auth: Authenticator = None
    db: Database = None


G = Globals()
