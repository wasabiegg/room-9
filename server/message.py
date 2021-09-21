from dataclasses import dataclass
import json
import time
from user import User


@dataclass
class Message:
    username: str
    content: str
    created: float

    def to_bytes(self) -> bytes:
        data = {
            "username": self.username,
            "content": self.content,
            "created": self.created,
        }
        return json.dumps(data).encode("utf-8")

    @classmethod
    def new(cls, message: str, user: User) -> "Message":
        return Message(username=user.username, content=message, created=time.time())
