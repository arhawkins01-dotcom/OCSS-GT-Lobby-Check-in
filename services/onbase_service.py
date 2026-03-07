from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import requests
import streamlit as st


class OnBaseAPIError(RuntimeError):
    """Raised for expected OnBase API failures that should show user-safe messages."""


def _require_secret(key: str) -> str:
    value = st.secrets.get(key)
    if not value:
        raise OnBaseAPIError(f"Missing required secret: {key}")
    return str(value)


@st.cache_data(ttl=3300, show_spinner=False)
def get_onbase_token() -> str:
    """Fetch OAuth2 bearer token using the client_credentials grant."""
    idp_url = _require_secret("IDP_URL").rstrip("/")
    client_id = _require_secret("CLIENT_ID")
    client_secret = _require_secret("CLIENT_SECRET")

    token_url = f"{idp_url}/idp/connect/token"

    try:
        response = requests.post(
            token_url,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=20,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        raise OnBaseAPIError(f"Token request failed (HTTP {status_code}).") from exc
    except requests.RequestException as exc:
        raise OnBaseAPIError("Token request failed due to a network error.") from exc

    token = response.json().get("access_token")
    if not token:
        raise OnBaseAPIError("Token response did not include access_token.")
    return token


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def find_appointment(case_number: str, token: str) -> Optional[dict[str, Any]]:
    """
    Lookup the first matching Genetic Testing Application document by Case Number.

    Note: OnBase endpoint query parameter names can vary by tenant. If needed,
    adjust the params mapping for your environment.
    """
    base_url = _require_secret("BASE_URL").rstrip("/")
    url = f"{base_url}/api/documents"

    params = {
        "documentTypeName": "Genetic Testing Application",
        "keywordName": "Case Number",
        "keywordValue": str(case_number).strip(),
        "pageSize": 1,
    }

    try:
        response = requests.get(url, headers=_headers(token), params=params, timeout=20)
        if response.status_code == 404:
            return None
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        if status_code == 401:
            raise OnBaseAPIError("Unauthorized when searching appointments.") from exc
        raise OnBaseAPIError(f"Appointment lookup failed (HTTP {status_code}).") from exc
    except requests.RequestException as exc:
        raise OnBaseAPIError("Appointment lookup failed due to a network error.") from exc

    items = response.json().get("items", [])
    if not items:
        return None

    doc = items[0]
    return {
        "doc_id": doc.get("id"),
        "status": doc.get("status") or doc.get("workflowStatus") or "UNKNOWN",
    }


def update_checkin_keywords(doc_id: int | str, token: str) -> None:
    """Update document check-in keywords to Arrived + timestamp."""
    base_url = _require_secret("BASE_URL").rstrip("/")
    url = f"{base_url}/api/documents/{doc_id}/keywords"

    payload = {
        "keywords": [
            {"name": "Check-In Status", "value": "Arrived"},
            {
                "name": "Check-In Timestamp",
                "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        ]
    }

    try:
        response = requests.post(url, headers=_headers(token), json=payload, timeout=20)
        if response.status_code == 401:
            raise OnBaseAPIError("Unauthorized when updating check-in keywords.")
        if response.status_code == 404:
            raise OnBaseAPIError("Document not found while updating check-in keywords.")
        response.raise_for_status()
    except requests.RequestException as exc:
        if isinstance(exc, OnBaseAPIError):
            raise
        raise OnBaseAPIError("Failed to update check-in keywords.") from exc


def trigger_workflow_checkin(doc_id: int | str, token: str) -> None:
    """
    Trigger the configured ad-hoc workflow task for kiosk check-in.

    Expected secret: KIOSK_CHECKIN_TASK_ID
    """
    base_url = _require_secret("BASE_URL").rstrip("/")
    task_id = _require_secret("KIOSK_CHECKIN_TASK_ID")
    url = f"{base_url}/api/workflow/tasks/{task_id}/execute"

    payload = {
        "documentId": doc_id,
        "taskName": "Kiosk Check-In",
    }

    try:
        response = requests.post(url, headers=_headers(token), json=payload, timeout=20)
        if response.status_code == 401:
            raise OnBaseAPIError("Unauthorized when triggering workflow check-in.")
        if response.status_code == 404:
            raise OnBaseAPIError("Workflow task not found for kiosk check-in.")
        response.raise_for_status()
    except requests.RequestException as exc:
        if isinstance(exc, OnBaseAPIError):
            raise
        raise OnBaseAPIError("Failed to trigger workflow check-in.") from exc


def perform_onbase_checkin(case_number: str) -> dict[str, Any]:
    """End-to-end check-in orchestration for OnBase mode."""
    token = get_onbase_token()
    appointment = find_appointment(case_number=case_number, token=token)

    if not appointment:
        return {"found": False}

    doc_id = appointment.get("doc_id")
    if not doc_id:
        raise OnBaseAPIError("Appointment was found but document ID was missing.")

    update_checkin_keywords(doc_id=doc_id, token=token)
    trigger_workflow_checkin(doc_id=doc_id, token=token)

    return {
        "found": True,
        "doc_id": doc_id,
        "status": appointment.get("status", "UNKNOWN"),
    }
