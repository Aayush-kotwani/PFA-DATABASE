"""Role-based access control (RBAC) tests across admin-only endpoints (Step B10)."""


def test_volunteer_forbidden_and_admin_allowed_on_admin_routes(
    client, admin_headers, volunteer_headers, sample_area
):
    """Verify volunteer receives 403 FORBIDDEN on all admin routes while admin succeeds."""
    # Create a dog as volunteer so DELETE /api/dogs/<id> has a real target
    dog_res = client.post(
        "/api/dogs",
        json={"area_id": sample_area.id, "sex": "male"},
        headers=volunteer_headers,
    )
    assert dog_res.status_code == 201
    dog_id = dog_res.get_json()["id"]

    # Volunteer must receive 403 on all admin-only routes
    assert client.get("/api/users", headers=volunteer_headers).status_code == 403
    assert (
        client.post(
            "/api/users",
            json={
                "name": "Blocked User",
                "email": "blocked@ngo.org",
                "password": "Password123!",
            },
            headers=volunteer_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/areas",
            json={
                "name": "Blocked Zone",
                "short_code": "BLK",
                "ward_no": "Ward 9",
                "color_name": "Coral",
                "color_hex": "#F43F5E",
            },
            headers=volunteer_headers,
        ).status_code
        == 403
    )
    assert client.delete(f"/api/dogs/{dog_id}", headers=volunteer_headers).status_code == 403
    assert client.get("/api/audit-logs", headers=volunteer_headers).status_code == 403
    assert client.get("/api/export/excel", headers=volunteer_headers).status_code == 403
    assert client.get("/api/analytics/export", headers=volunteer_headers).status_code == 403

    # Admin must succeed on every one of those routes
    assert client.get("/api/users", headers=admin_headers).status_code == 200
    assert (
        client.post(
            "/api/users",
            json={
                "name": "Allowed Volunteer",
                "email": "allowed@ngo.org",
                "password": "Password123!",
                "role": "volunteer",
            },
            headers=admin_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/areas",
            json={
                "name": "South Zone - Ward 4",
                "short_code": "STH",
                "ward_no": "Ward 4",
                "color_name": "Rose",
                "color_hex": "#E11D48",
            },
            headers=admin_headers,
        ).status_code
        == 201
    )
    assert client.get("/api/audit-logs", headers=admin_headers).status_code == 200
    assert client.get("/api/export/excel", headers=admin_headers).status_code == 200
    assert client.get("/api/analytics/export", headers=admin_headers).status_code == 200
    assert client.delete(f"/api/dogs/{dog_id}", headers=admin_headers).status_code == 200
