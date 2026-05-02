import os

import pytest
import requests

from server import LLMService


# Base URL and API smoke checks
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="session")
def base_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


# Auth module coverage
def test_health_is_healthy_and_live_sarvam_mode(api_client, base_url):
    response = api_client.get(f"{base_url}/api/health", timeout=20)
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "healthy"
    assert payload["mock_external_services"] is False
    assert isinstance(payload["timestamp"], str) and payload["timestamp"]


def test_demo_login_still_works(api_client, base_url):
    response = api_client.post(
        f"{base_url}/api/auth/login",
        json={"email": "doctor@clinic.test", "password": "demo1234"},
        timeout=20,
    )
    assert response.status_code == 200
    payload = response.json()

    assert isinstance(payload.get("token"), str) and payload["token"]
    assert payload["user"]["email"] == "doctor@clinic.test"


# Gemini prescription extraction service coverage
@pytest.mark.asyncio
async def test_gemini_extraction_returns_required_structured_fields():
    llm_service = LLMService()
    consultation_text = (
        "Patient has burning urination and lower abdominal pain for 2 days. "
        "Diagnosed as uncomplicated UTI. Prescribed nitrofurantoin 100 mg twice daily for 5 days. "
        "Drink more water and return if fever develops. Follow up in 5 days."
    )

    structured, warning = await llm_service.extract_prescription(consultation_text, "pytest-gemini-1")

    assert warning == ""
    assert set(structured.keys()) == {"symptoms", "diagnosis", "medications", "advice", "follow_up"}
    assert isinstance(structured["symptoms"], list)
    assert isinstance(structured["diagnosis"], str)
    assert isinstance(structured["medications"], list)
    assert isinstance(structured["advice"], list)
    assert isinstance(structured["follow_up"], str)


@pytest.mark.asyncio
async def test_gemini_extraction_is_not_static_previous_mock_for_arbitrary_text():
    llm_service = LLMService()
    arbitrary_text = (
        "Patient reports migraine with photophobia and nausea since yesterday. "
        "Assessment: acute migraine attack. Start ibuprofen 400 mg as needed after meals. "
        "Advise hydration, sleep hygiene, and reduce screen time. Review in one week."
    )

    structured, warning = await llm_service.extract_prescription(arbitrary_text, "pytest-gemini-2")

    assert warning == ""

    flattened = " ".join(
        [
            " ".join(structured.get("symptoms", [])),
            structured.get("diagnosis", ""),
            " ".join(structured.get("medications", [])),
            " ".join(structured.get("advice", [])),
            structured.get("follow_up", ""),
        ]
    ).lower()

    # Guard against old fixed mocked output pattern from previous iterations.
    assert "sore throat" not in flattened
    assert "dry cough" not in flattened
    assert "paracetamol 500 mg" not in flattened

    # Ensure extraction reflects this arbitrary input rather than a static template.
    assert "migraine" in flattened
    assert "ibuprofen" in flattened