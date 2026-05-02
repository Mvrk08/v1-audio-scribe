import io
import os
import time

import pytest
import requests


# Core config and auth flows
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


@pytest.fixture(scope="session")
def auth_token(api_client, base_url):
    response = api_client.post(
        f"{base_url}/api/auth/login",
        json={"email": "doctor@clinic.test", "password": "demo1234"},
        timeout=20,
    )
    if response.status_code != 200:
        pytest.skip(f"Login failed: {response.status_code} {response.text}")
    data = response.json()
    assert isinstance(data.get("token"), str) and data["token"]
    assert data["user"]["email"] == "doctor@clinic.test"
    return data["token"]


@pytest.fixture
def authed_client(api_client, auth_token):
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


def _create_session(authed_client, base_url, source="auto", target="en"):
    response = authed_client.post(
        f"{base_url}/api/v1/sessions",
        json={"source_language": source, "target_language": target},
        timeout=20,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["source_language"] == source
    assert data["target_language"] == target
    assert data["status"] == "created"
    assert isinstance(data["id"], str) and data["id"]
    return data


# Health and authentication checks
def test_health_endpoint(api_client, base_url):
    response = api_client.get(f"{base_url}/api/health", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert isinstance(data["mock_external_services"], bool)
    assert "timestamp" in data


def test_protected_endpoint_requires_auth(api_client, base_url):
    response = api_client.get(f"{base_url}/api/auth/session", timeout=20)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_login_success(api_client, base_url):
    response = api_client.post(
        f"{base_url}/api/auth/login",
        json={"email": "doctor@clinic.test", "password": "demo1234"},
        timeout=20,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["token"], str)
    assert data["user"]["email"] == "doctor@clinic.test"


# Session workflow: create, upload, process, poll, result, update, delete
def test_full_session_workflow_with_persistence_checks(authed_client, base_url):
    created = _create_session(authed_client, base_url, source="auto", target="hi")
    session_id = created["id"]

    audio_bytes = b"RIFF" + (b"a" * 4096)
    files = {"file": ("test-audio.wav", io.BytesIO(audio_bytes), "audio/wav")}
    upload = authed_client.post(
        f"{base_url}/api/v1/sessions/{session_id}/audio",
        files=files,
        data={"duration_seconds": "45"},
        timeout=30,
    )
    assert upload.status_code == 200, upload.text
    upload_data = upload.json()
    assert upload_data["status"] == "uploaded"
    assert upload_data["original_filename"] == "test-audio.wav"

    process = authed_client.post(f"{base_url}/api/v1/sessions/{session_id}/process", timeout=20)
    assert process.status_code == 200, process.text
    process_data = process.json()
    assert process_data["status"] == "running"

    status_data = None
    for _ in range(12):
        status_response = authed_client.get(f"{base_url}/api/v1/sessions/{session_id}/status", timeout=20)
        assert status_response.status_code == 200
        status_data = status_response.json()
        if status_data["status"] == "completed":
            break
        time.sleep(1)

    assert status_data is not None
    assert status_data["status"] == "completed"

    result = authed_client.get(f"{base_url}/api/v1/sessions/{session_id}/result", timeout=20)
    assert result.status_code == 200, result.text
    result_data = result.json()
    assert result_data["session"]["id"] == session_id
    assert isinstance(result_data["raw_transcript"], str) and result_data["raw_transcript"]
    assert isinstance(result_data["translated_text"], str) and result_data["translated_text"]
    assert isinstance(result_data["structured_prescription"]["medications"], list)
    assert any("MOCKED" in warning for warning in result_data["warnings"])

    updated_payload = {
        "raw_transcript": f"{result_data['raw_transcript']} (edited)",
        "translated_text": result_data["translated_text"],
        "structured_prescription": result_data["structured_prescription"],
    }
    update = authed_client.patch(
        f"{base_url}/api/v1/sessions/{session_id}/result",
        json=updated_payload,
        timeout=20,
    )
    assert update.status_code == 200, update.text
    update_data = update.json()
    assert update_data["raw_transcript"].endswith("(edited)")

    verify = authed_client.get(f"{base_url}/api/v1/sessions/{session_id}/result", timeout=20)
    assert verify.status_code == 200
    assert verify.json()["raw_transcript"].endswith("(edited)")

    delete = authed_client.delete(f"{base_url}/api/v1/sessions/{session_id}", timeout=20)
    assert delete.status_code == 200
    assert delete.json()["status"] == "deleted"

    missing = authed_client.get(f"{base_url}/api/v1/sessions/{session_id}/status", timeout=20)
    assert missing.status_code == 404


def test_unsupported_audio_extension_rejected(authed_client, base_url):
    created = _create_session(authed_client, base_url)
    session_id = created["id"]
    files = {"file": ("invalid.txt", io.BytesIO(b"not-audio"), "text/plain")}
    response = authed_client.post(
        f"{base_url}/api/v1/sessions/{session_id}/audio",
        files=files,
        data={"duration_seconds": "10"},
        timeout=20,
    )
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]


def test_audio_over_25mb_rejected(authed_client, base_url):
    created = _create_session(authed_client, base_url)
    session_id = created["id"]
    huge_audio = io.BytesIO(b"a" * (26 * 1024 * 1024))
    files = {"file": ("too-large.wav", huge_audio, "audio/wav")}
    response = authed_client.post(
        f"{base_url}/api/v1/sessions/{session_id}/audio",
        files=files,
        data={"duration_seconds": "30"},
        timeout=60,
    )
    assert response.status_code == 413
    assert "25MB" in response.json()["detail"]


def test_audio_duration_over_2_minutes_rejected(authed_client, base_url):
    created = _create_session(authed_client, base_url)
    session_id = created["id"]
    files = {"file": ("ok.wav", io.BytesIO(b"RIFF" + b"b" * 2048), "audio/wav")}
    response = authed_client.post(
        f"{base_url}/api/v1/sessions/{session_id}/audio",
        files=files,
        data={"duration_seconds": "121"},
        timeout=20,
    )
    assert response.status_code == 413
    assert "2 minute" in response.json()["detail"]


# History and delete behavior
def test_history_lists_completed_sessions_and_supports_delete(authed_client, base_url):
    created = _create_session(authed_client, base_url, source="en", target="en")
    session_id = created["id"]
    files = {"file": ("history.wav", io.BytesIO(b"RIFF" + b"c" * 4096), "audio/wav")}
    upload = authed_client.post(
        f"{base_url}/api/v1/sessions/{session_id}/audio",
        files=files,
        data={"duration_seconds": "25"},
        timeout=30,
    )
    assert upload.status_code == 200
    process = authed_client.post(f"{base_url}/api/v1/sessions/{session_id}/process", timeout=20)
    assert process.status_code == 200

    for _ in range(12):
        status_response = authed_client.get(f"{base_url}/api/v1/sessions/{session_id}/status", timeout=20)
        assert status_response.status_code == 200
        if status_response.json()["status"] == "completed":
            break
        time.sleep(1)

    sessions = authed_client.get(f"{base_url}/api/v1/sessions", timeout=20)
    assert sessions.status_code == 200
    list_data = sessions.json()
    match = next((item for item in list_data if item["id"] == session_id), None)
    assert match is not None
    assert match["has_result"] is True

    delete = authed_client.delete(f"{base_url}/api/v1/sessions/{session_id}", timeout=20)
    assert delete.status_code == 200
