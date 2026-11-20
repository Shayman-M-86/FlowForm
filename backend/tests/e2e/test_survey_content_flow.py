"""Verify the version metadata and content contracts through HTTP and PostgreSQL."""

from flask.testing import FlaskClient

from tests.e2e.conftest import SeedData


def test_empty_draft_and_stale_content_save(authed_client: FlaskClient, seed: SeedData) -> None:
    authed_client.environ_base["REMOTE_ADDR"] = "192.0.2.1"
    versions_url = f"/api/v1/studio/projects/{seed.project.id}/surveys/{seed.survey.id}/versions"
    response = authed_client.post(versions_url)
    assert response.status_code == 201, response.get_json()
    draft = response.get_json()
    assert draft["revision"] == 0
    read_url = f"{versions_url}/{draft['version_number']}"
    save_url = f"{versions_url}/{draft['version_id']}/content"

    response = authed_client.get(read_url)
    assert response.status_code == 200
    assert response.get_json() == {
        "version_id": draft["version_id"],
        "status": "draft",
        "revision": 0,
        "content": None,
    }

    content = {"title": "Edited survey", "sections": []}
    expected_content = {**content, "description": None, "workflow": None}
    response = authed_client.put(save_url, json={"expected_revision": 0, "content": content})
    assert response.status_code == 200, response.get_json()
    assert response.get_json() == {"revision": 1}

    response = authed_client.put(save_url, json={"expected_revision": 0, "content": {"title": "Stale", "sections": []}})
    assert response.status_code == 409
    assert response.get_json()["details"]["current_revision"] == 1

    response = authed_client.get(read_url)
    assert response.status_code == 200
    assert response.get_json() == {
        "version_id": draft["version_id"],
        "status": "draft",
        "revision": 1,
        "content": expected_content,
    }

    response = authed_client.put(
        f"{versions_url}/{seed.published_version.id}/content",
        json={"expected_revision": seed.published_version.revision, "content": content},
    )
    assert response.status_code == 409
    assert response.get_json()["code"] == "VERSION_NOT_EDITABLE"
