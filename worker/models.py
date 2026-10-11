import faust


class Message(faust.Record, serializer="json"):
    sender_id: str
    recipient_id: str
    text: str


class BlockCommand(faust.Record, serializer="json"):
    user_id: str
    target_id: str
