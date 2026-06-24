import json


def handler(event: dict, context) -> dict:
    print(f"Method: {event.get('httpMethod')} Path: {event.get('path')}")
    print(f"Event: {json.dumps(event)}")

    return {
        "statusCode": 200,
        "body": "ok",
    }
