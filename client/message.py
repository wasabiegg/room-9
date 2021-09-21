import time
from dataclasses import dataclass
import json


@dataclass
class Message:
    username: str
    content: str
    created: float

    @classmethod
    def new(cls, src: str) -> "Message":
        data = json.loads(src)
        return Message(
            username=data["username"], content=data["content"], created=data["created"]
        )

    def __str__(self) -> str:
        created_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created))
        return f"{created_str} - [{self.username}] => {self.content}"
