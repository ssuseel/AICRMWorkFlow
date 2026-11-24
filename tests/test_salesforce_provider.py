"""Salesforce adapter tests with an offline HTTP fake."""

from src.integrations.crm.base import CRMPermanentError
from src.integrations.crm.salesforce_provider import SalesforceProvider


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload
        self.content = b"" if status_code == 204 else b"response"

    def json(self):
        return self.payload


class FakeHTTPSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.posts = []
        self.requests = []

    def post(self, url, data, timeout):
        self.posts.append((url, data))
        return self.responses.pop(0)

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.responses.pop(0)


def provider_with_responses(responses):
    http = FakeHTTPSession(responses)
    provider = SalesforceProvider(
        "client-id",
        "client-secret",
        http_session=http,
    )
    return provider, http


def test_salesforce_creates_lead_using_oauth_and_field_mapping():
    provider, http = provider_with_responses(
        [
            FakeResponse(
                200,
                {
                    "access_token": "temporary-token",
                    "instance_url": "https://example.my.salesforce.com",
                },
            ),
            FakeResponse(200, {"records": []}),
            FakeResponse(201, {"id": "00Q123"}),
        ]
    )

    result = provider.upsert_lead(
        {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "company": "Analytical Engines",
            "title": "Engineer",
        },
        {"title": "Title"},
        "idempotency-key",
    )

    assert result.provider == "salesforce"
    assert result.external_id == "00Q123"
    assert result.created
    assert http.posts[0][1]["grant_type"] == "client_credentials"
    create_call = http.requests[-1]
    assert create_call[0] == "POST"
    assert create_call[2]["json"]["LastName"] == "Lovelace"
    assert create_call[2]["json"]["Company"] == "Analytical Engines"
    assert create_call[2]["json"]["Title"] == "Engineer"


def test_salesforce_updates_matching_email_instead_of_creating_duplicate():
    provider, http = provider_with_responses(
        [
            FakeResponse(
                200,
                {
                    "access_token": "temporary-token",
                    "instance_url": "https://example.my.salesforce.com",
                },
            ),
            FakeResponse(200, {"records": [{"Id": "00QExisting"}]}),
            FakeResponse(204, {}),
        ]
    )
    result = provider.upsert_lead(
        {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "company": "Analytical Engines",
        },
        {},
        "idempotency-key",
    )
    assert result.external_id == "00QExisting"
    assert not result.created
    assert http.requests[-1][0] == "PATCH"


def test_salesforce_rejects_missing_company_before_api_call():
    provider, http = provider_with_responses([])
    try:
        provider.upsert_lead(
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
            },
            {},
            "key",
        )
    except CRMPermanentError as exc:
        assert "company" in str(exc).lower()
    else:
        raise AssertionError("Missing Salesforce-required company was accepted")
    assert http.posts == []


def test_salesforce_task_uses_custom_idempotency_field():
    provider, http = provider_with_responses(
        [
            FakeResponse(
                200,
                {
                    "access_token": "temporary-token",
                    "instance_url": "https://example.my.salesforce.com",
                },
            ),
            FakeResponse(200, {"records": []}),
            FakeResponse(201, {"id": "00T123"}),
        ]
    )
    result = provider.create_task(
        {"Subject": "Call lead", "Status": "Not Started"},
        "task-key-123",
    )
    assert result.entity_type == "task"
    assert result.external_id == "00T123"
    assert http.requests[-1][2]["json"]["AICRM_Idempotency_Key__c"] == "task-key-123"


def test_salesforce_upserts_contact_by_email():
    provider, http = provider_with_responses(
        [
            FakeResponse(
                200,
                {
                    "access_token": "temporary-token",
                    "instance_url": "https://example.my.salesforce.com",
                },
            ),
            FakeResponse(200, {"records": []}),
            FakeResponse(201, {"id": "003123"}),
        ]
    )
    result = provider.upsert_contact(
        {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "phone": "555-0100",
        },
        {},
        "contact-key",
    )
    assert result.entity_type == "contact"
    assert result.external_id == "003123"
    assert http.requests[-1][1].endswith("/sobjects/Contact")


def test_salesforce_upserts_account_by_name():
    provider, http = provider_with_responses(
        [
            FakeResponse(
                200,
                {
                    "access_token": "temporary-token",
                    "instance_url": "https://example.my.salesforce.com",
                },
            ),
            FakeResponse(200, {"records": []}),
            FakeResponse(201, {"id": "001123"}),
        ]
    )
    result = provider.upsert_account(
        {"Name": "Analytical Engines"},
        "account-key",
    )
    assert result.entity_type == "account"
    assert result.external_id == "001123"
    assert http.requests[-1][1].endswith("/sobjects/Account")


def test_salesforce_associates_contact_to_account():
    provider, http = provider_with_responses(
        [
            FakeResponse(
                200,
                {
                    "access_token": "temporary-token",
                    "instance_url": "https://example.my.salesforce.com",
                },
            ),
            FakeResponse(204, {}),
        ]
    )
    provider.associate_contact_account("003123", "001123")
    method, url, kwargs = http.requests[-1]
    assert method == "PATCH"
    assert url.endswith("/sobjects/Contact/003123")
    assert kwargs["json"] == {"AccountId": "001123"}
