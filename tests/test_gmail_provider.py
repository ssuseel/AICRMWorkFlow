"""Gmail adapter unit tests using fake Google API responses."""

import base64

from src.integrations.email.gmail_provider import GmailProvider


class FakeExecute:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def send(self, userId, body):
        if self.error:
            raise self.error
        return FakeExecute(self.response)

    def list(self, userId, q):
        if self.error:
            raise self.error
        return FakeExecute(self.response)

    def get(self, userId, id, format):
        if self.error:
            raise self.error
        return FakeExecute(self.response)


class FakeMessageService:
    def __init__(self, list_response, message_response):
        self.list_response = list_response
        self.message_response = message_response

    def list(self, userId, q):
        return FakeExecute(self.list_response)

    def get(self, userId, id, format):
        return FakeExecute(self.message_response)


class FakeIncomingUsers:
    def __init__(self, message_service):
        self.message_service = message_service

    def messages(self):
        return self.message_service

    def threads(self):
        return FakeThreads()


class FakeIncomingService:
    def __init__(self, list_response, message_response):
        self.users_value = FakeIncomingUsers(
            FakeMessageService(list_response, message_response)
        )

    def users(self):
        return self.users_value


class FakeUsers:
    def __init__(self, messages):
        self.messages_value = messages

    def messages(self):
        return self.messages_value

    def threads(self):
        return FakeThreads()


class FakeThreads:
    def get(self, userId, id):
        return FakeExecute({"id": id, "messages": [{"id": "m1"}]})


class FakeService:
    def __init__(self, messages):
        self.users_value = FakeUsers(messages)

    def users(self):
        return self.users_value


def make_provider(messages):
    provider = object.__new__(GmailProvider)
    provider.sender = "sender@example.com"
    provider.service = FakeService(messages)
    return provider


def test_gmail_send_maps_thread_and_message_ids():
    provider = make_provider(
        FakeMessages({"id": "message-123", "threadId": "thread-456"})
    )

    result = provider.send("customer@example.com", "Subject", "Body")

    assert result.provider == "gmail"
    assert result.provider_message_id == "message-123"
    assert result.thread_id == "thread-456"
    assert result.status == "SENT"


def test_gmail_fetch_incoming_decodes_plain_text():
    encoded = base64.urlsafe_b64encode(b"Please send details").decode("ascii")
    message = {
        "id": "message-123",
        "threadId": "thread-456",
        "payload": {
            "headers": [
                {"name": "From", "value": "customer@example.com"},
                {"name": "To", "value": "sender@example.com"},
                {"name": "Subject", "value": "Information request"},
            ],
            "parts": [{"mimeType": "text/plain", "body": {"data": encoded}}],
        },
    }
    provider = make_provider(FakeMessages({"messages": [{"id": "message-123"}]}))
    provider.service = FakeIncomingService(
        {"messages": [{"id": "message-123"}]},
        message,
    )

    messages = provider.fetch_incoming()
    assert len(messages) == 1
    assert messages[0].provider_message_id == "message-123"
    assert messages[0].thread_id == "thread-456"
    assert messages[0].body == "Please send details"


def test_gmail_thread_retrieval():
    provider = make_provider(FakeMessages())
    thread = provider.get_thread("thread-456")
    assert thread["id"] == "thread-456"
    assert thread["messages"][0]["id"] == "m1"
