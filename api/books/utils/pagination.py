import base64
import json
from typing import Optional


def encode_token(last_evaluated_key: Optional[dict]) -> Optional[str]:
    if not last_evaluated_key:
        return None
    return base64.b64encode(json.dumps(last_evaluated_key).encode()).decode()


def decode_token(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    return json.loads(base64.b64decode(token.encode()).decode())
