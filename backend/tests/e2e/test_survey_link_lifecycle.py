"""End-to-end survey-link lifecycle: create -> list -> resolve -> update -> delete.

Every step goes through the real HTTP routes against a real Postgres, so the
service/repo/DB wiring is exercised as a client would hit it. The create step
is the direct regression guard for the bug where ``create_link`` omitted the
NOT NULL ``project_id`` column: that path is only reachable through the route,
never through the hand-rolled inserts the integration tests use.
"""

from __future__ import annotations

from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app.schema.orm.core.survey_access import SurveyLink
from tests.e2e.conftest import SeedData


def _links_url(seed: SeedData) -> str:
    return f"/api/v1/projects/{seed.project.id}/surveys/{seed.survey.id}/links"


def test_create_link_populates_project_id(
    authed_client: FlaskClient, seed: SeedData, core_db_session: Session
) -> None:
    """POSTing a link succeeds and the persisted row carries the survey's project_id.

    Regression: the repo previously never set project_id, so this 201 came back
    as a 500 (NOT NULL violation) from Postgres. project_id is an internal
    scoping column and is not exposed in the API response, so we read it back
    off the persisted row directly.
    """
    resp = authed_client.post(_links_url(seed), json={"name": "launch link"})

    assert resp.status_code == 201, f"expected 201, got {resp.status_code}: {resp.get_data(as_text=True)}"
    body = resp.get_json()
    assert body["link"]["survey_id"] == seed.survey.id
    assert body["link"]["name"] == "launch link"
    assert body["token"], "expected a token in the create response"
    assert body["url"], "expected a public url in the create response"

    # project_id is not in the response shape; verify it persisted on the row.
    link = core_db_session.get(SurveyLink, body["link"]["id"])
    assert link is not None, "created link was not persisted"
    assert link.project_id == seed.project.id, (
        f"link.project_id={link.project_id!r}, expected {seed.project.id!r}"
    )


def test_link_lifecycle_create_list_resolve_update_delete(
    authed_client: FlaskClient, seed: SeedData
) -> None:
    """Walk a link through its full lifecycle via the public + admin routes."""
    links_url = _links_url(seed)

    # --- create ---
    create = authed_client.post(links_url, json={"name": "lifecycle link"})
    assert create.status_code == 201, create.get_data(as_text=True)
    created = create.get_json()
    link_id = created["link"]["id"]
    token = created["token"]

    # --- list: the new link shows up ---
    listed = authed_client.get(links_url)
    assert listed.status_code == 200, listed.get_data(as_text=True)
    ids = [link["id"] for link in listed.get_json()["links"]]
    assert link_id in ids, f"created link {link_id} not in list {ids}"

    # --- resolve: the public token maps back to the seeded survey ---
    resolve = authed_client.post("/api/v1/public/links/resolve", json={"token": token})
    assert resolve.status_code == 200, resolve.get_data(as_text=True)
    resolved = resolve.get_json()
    assert resolved["survey"]["id"] == seed.survey.id
    assert resolved["published_version"]["id"] == seed.published_version.id

    # --- update: deactivate and rename ---
    update = authed_client.patch(
        f"{links_url}/{link_id}",
        json={"is_active": False, "name": "renamed link"},
    )
    assert update.status_code == 200, update.get_data(as_text=True)
    updated = update.get_json()
    assert updated["is_active"] is False
    assert updated["name"] == "renamed link"

    # --- delete ---
    delete = authed_client.delete(f"{links_url}/{link_id}")
    assert delete.status_code == 204, delete.get_data(as_text=True)

    # --- list again: the link is gone ---
    after = authed_client.get(links_url)
    assert after.status_code == 200, after.get_data(as_text=True)
    remaining = [link["id"] for link in after.get_json()["links"]]
    assert link_id not in remaining, f"deleted link {link_id} still present in {remaining}"
