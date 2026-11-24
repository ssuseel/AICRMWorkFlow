"""Salesforce REST API adapter using OAuth client credentials."""

import re
from typing import Any
from urllib.parse import quote

import requests
from requests import Session
from requests.exceptions import ConnectionError, Timeout

from src.domain.schemas import CRMUpsertResult
from src.integrations.crm.base import (
    CRMPermanentError,
    CRMProvider,
    CRMTransientError,
)

DEFAULT_LEAD_MAPPING = {
    "first_name": "FirstName",
    "last_name": "LastName",
    "email": "Email",
    "phone": "Phone",
    "company": "Company",
    "title": "Title",
    "industry": "Industry",
    "source": "LeadSource",
}


class SalesforceProvider(CRMProvider):
    provider_name = "salesforce"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        login_url: str = "https://login.salesforce.com",
        api_version: str = "v60.0",
        task_idempotency_field: str = "AICRM_Idempotency_Key__c",
        http_session: Session | None = None,
    ) -> None:
        if not client_id or not client_secret:
            raise CRMPermanentError(
                "Salesforce requires a connected app client ID and client secret"
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self.login_url = login_url.rstrip("/")
        self.api_version = api_version
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", task_idempotency_field):
            raise CRMPermanentError("Invalid Salesforce task idempotency field")
        self.task_idempotency_field = task_idempotency_field
        self.http = http_session or requests.Session()
        self.access_token: str | None = None
        self.instance_url: str | None = None

    def _authenticate(self) -> None:
        try:
            response = self.http.post(
                f"{self.login_url}/services/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=20,
            )
        except (ConnectionError, Timeout) as exc:
            raise CRMTransientError(
                "Salesforce OAuth is temporarily unavailable"
            ) from exc
        if response.status_code == 429 or response.status_code >= 500:
            raise CRMTransientError("Salesforce OAuth is temporarily unavailable")
        if response.status_code >= 400:
            raise CRMPermanentError("Salesforce OAuth credentials were rejected")
        try:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.instance_url = token_data["instance_url"].rstrip("/")
        except (KeyError, ValueError) as exc:
            raise CRMPermanentError("Salesforce OAuth response was invalid") from exc

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.access_token or not self.instance_url:
            self._authenticate()
        try:
            response = self.http.request(
                method,
                f"{self.instance_url}/services/data/{self.api_version}{path}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params=params,
                json=json,
                timeout=30,
            )
        except (ConnectionError, Timeout) as exc:
            raise CRMTransientError(
                "Salesforce API is temporarily unavailable"
            ) from exc
        if response.status_code == 429 or response.status_code >= 500:
            raise CRMTransientError("Salesforce API is temporarily unavailable")
        if response.status_code >= 400:
            raise CRMPermanentError(
                f"Salesforce rejected the CRM operation (HTTP {response.status_code})"
            )
        if response.status_code == 204 or not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise CRMPermanentError("Salesforce returned an invalid response") from exc

    def _query(self, soql: str) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "/query",
            params={"q": soql},
        ).get("records", [])

    def _upsert_by_email(
        self,
        object_name: str,
        email: str,
        fields: dict[str, Any],
    ) -> tuple[str, bool]:
        escaped = email.replace("\\", "\\\\").replace("'", "\\'")
        query = (
            f"SELECT Id FROM {object_name} "
            f"WHERE Email = '{escaped}' ORDER BY CreatedDate ASC LIMIT 1"
        )
        matches = self._query(query)
        if matches:
            record_id = str(matches[0]["Id"])
            self._request(
                "PATCH",
                f"/sobjects/{object_name}/{quote(record_id, safe='')}",
                json=fields,
            )
            return record_id, False
        result = self._request("POST", f"/sobjects/{object_name}", json=fields)
        if not result.get("id"):
            raise CRMPermanentError("Salesforce create response omitted record ID")
        return str(result["id"]), True

    @staticmethod
    def _result(entity: str, record_id: str, created: bool) -> CRMUpsertResult:
        return CRMUpsertResult(
            provider="salesforce",
            external_id=record_id,
            entity_type=entity,
            created=created,
        )

    def upsert_lead(
        self,
        lead: dict[str, Any],
        field_mapping: dict[str, str],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        del idempotency_key
        mapping = DEFAULT_LEAD_MAPPING | field_mapping
        fields = {
            remote: lead[local]
            for local, remote in mapping.items()
            if local in lead and lead[local] is not None
        }
        if not fields.get("LastName") or not fields.get("Company"):
            raise CRMPermanentError(
                "Salesforce Lead requires last name and company; provide field values before sync"
            )
        email = str(lead.get("email") or "")
        if not email:
            raise CRMPermanentError("Salesforce lead sync requires an email address")
        record_id, created = self._upsert_by_email("Lead", email, fields)
        return self._result("lead", record_id, created)

    def upsert_contact(
        self,
        contact: dict[str, Any],
        field_mapping: dict[str, str],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        del idempotency_key
        mapping = {
            "first_name": "FirstName",
            "last_name": "LastName",
            "email": "Email",
            "phone": "Phone",
            "title": "Title",
        } | field_mapping
        fields = {
            remote: contact[local]
            for local, remote in mapping.items()
            if local in contact and contact[local] is not None
        }
        if not fields.get("LastName"):
            raise CRMPermanentError("Salesforce Contact requires a last name")
        email = str(contact.get("email") or "")
        if not email:
            raise CRMPermanentError("Salesforce contact sync requires an email address")
        record_id, created = self._upsert_by_email("Contact", email, fields)
        return self._result("contact", record_id, created)

    def upsert_account(
        self,
        account: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        del idempotency_key
        name = str(account.get("Name") or account.get("name") or "").strip()
        if not name:
            raise CRMPermanentError("Salesforce Account requires a name")
        escaped = name.replace("\\", "\\\\").replace("'", "\\'")
        matches = self._query(
            f"SELECT Id FROM Account WHERE Name = '{escaped}' "
            "ORDER BY CreatedDate ASC LIMIT 1"
        )
        if matches:
            record_id = str(matches[0]["Id"])
            self._request(
                "PATCH",
                f"/sobjects/Account/{quote(record_id, safe='')}",
                json=account,
            )
            created = False
        else:
            result = self._request("POST", "/sobjects/Account", json=account)
            record_id = str(result.get("id") or "")
            if not record_id:
                raise CRMPermanentError("Salesforce Account response omitted record ID")
            created = True
        return self._result("account", record_id, created)

    def associate_contact_account(
        self,
        contact_id: str,
        account_id: str,
    ) -> None:
        self._request(
            "PATCH",
            f"/sobjects/Contact/{quote(contact_id, safe='')}",
            json={"AccountId": account_id},
        )

    def create_task(
        self,
        task: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        return self._upsert_task("task", task, idempotency_key)

    def log_activity(
        self,
        activity: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        return self._upsert_task("activity", activity, idempotency_key)

    def _upsert_task(
        self,
        entity_type: str,
        values: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        field = self.task_idempotency_field
        escaped = idempotency_key.replace("\\", "\\\\").replace("'", "\\'")
        matches = self._query(
            f"SELECT Id FROM Task WHERE {field} = '{escaped}' LIMIT 1"
        )
        task_values = dict(values)
        task_values[field] = idempotency_key
        if matches:
            record_id = str(matches[0]["Id"])
            self._request(
                "PATCH",
                f"/sobjects/Task/{quote(record_id, safe='')}",
                json=task_values,
            )
            created = False
        else:
            result = self._request("POST", "/sobjects/Task", json=task_values)
            record_id = str(result.get("id") or "")
            if not record_id:
                raise CRMPermanentError("Salesforce Task response omitted record ID")
            created = True
        return self._result(entity_type, record_id, created)
