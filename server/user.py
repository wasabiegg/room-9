from dataclasses import dataclass
from typing import Tuple


@dataclass
class User:
    username: str
    addr: Tuple[str, str]
