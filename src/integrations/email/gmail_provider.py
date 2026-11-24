"""Gmail API email provider adapter."""

import base64
from email.message import EmailMessage
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.domain.schemas import DeliveryResult, IncomingEmail
from src.integrations.email.base import (
    EmailPermanentError,
    EmailProvider,
    EmailTransientError,
)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


class GmailProvider(EmailProvider):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        sender: str,
    ) -> None:
        if not all((client_id, client_secret, refresh_token, sender)):
            raise EmailPermanentError(
                "Gmail requires client ID, client secret, refresh token, and sender"
            )
        self.sender = sender
        self.credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=GMAIL_SCOPES,
        )
        try:
            self.credentials.refresh(Request())
        except RefreshError as exc:
            raise EmailPermanentError(
                "Gmail OAuth credentials could not be refreshed"
            ) from exc
        self.service = build("gmail", "v1", credentials=self.credentials)

    def send(self, recipient: str, subject: str, body: str) -> DeliveryResult:
        message = EmailMessage()
        message["To"] = recipient
        message["From"] = self.sender
        message["Subject"] = subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        try:
            sent = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
        except HttpError as exc:
            status = exc.resp.status
            if status in {429, 500, 502, 503, 504}:
                raise EmailTransientError(
                    "Gmail delivery is temporarily unavailable"
                ) from exc
            raise EmailPermanentError("Gmail rejected the send request") from exc
        except Exception as exc:
            raise EmailTransientError("Gmail send failed unexpectedly") from exc

        return DeliveryResult(
            provider="gmail",
            provider_message_id=str(sent["id"]),
            thread_id=str(sent.get("threadId") or sent["id"]),
            status="SENT",
        )

    def fetch_incoming(self, since: str | None = None) -> list[IncomingEmail]:
        query = f"after:{since}" if since else "in:inbox"
        try:
            response = (
                self.service.users().messages().list(userId="me", q=query).execute()
            )
        except HttpError as exc:
            if exc.resp.status in {429, 500, 502, 503, 504}:
                raise EmailTransientError(
                    "Gmail retrieval is temporarily unavailable"
                ) from exc
            raise EmailPermanentError("Gmail retrieval was rejected") from exc

        incoming: list[IncomingEmail] = []
        for item in response.get("messages", []):
            incoming.append(self._get_message(item["id"]))
        return incoming

    def _get_message(self, message_id: str) -> IncomingEmail:
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except HttpError as exc:
            if exc.resp.status in {429, 500, 502, 503, 504}:
                raise EmailTransientError(
                    "Gmail retrieval is temporarily unavailable"
                ) from exc
            raise EmailPermanentError("Gmail message retrieval was rejected") from exc

        headers = {
            header["name"].lower(): header["value"]
            for header in message.get("payload", {}).get("headers", [])
        }
        body = self._extract_text(message.get("payload", {}))
        return IncomingEmail(
            provider_message_id=message_id,
            thread_id=str(message.get("threadId") or message_id),
            from_address=headers.get("from", ""),
            to_address=headers.get("to", ""),
            subject=headers.get("subject", ""),
            body=body,
        )

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                "utf-8", errors="replace"
            )
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get(
                "data"
            ):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                    "utf-8", errors="replace"
                )
            nested = GmailProvider._extract_text(part)
            if nested:
                return nested
        return ""

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        try:
            thread = (
                self.service.users().threads().get(userId="me", id=thread_id).execute()
            )
        except HttpError as exc:
            if exc.resp.status in {429, 500, 502, 503, 504}:
                raise EmailTransientError(
                    "Gmail thread retrieval is temporarily unavailable"
                ) from exc
            raise EmailPermanentError("Gmail thread retrieval was rejected") from exc
        return {"id": thread_id, "messages": thread.get("messages", [])}
