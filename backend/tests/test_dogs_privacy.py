"""Privacy tests for guardian_phone hiding and analytics PII exclusion (Step B10)."""


def test_guardian_phone_role_isolation_and_analytics_privacy(
    client, admin_headers, volunteer_headers, sample_area
):
    """Verify volunteers never see or overwrite guardian_phone, and analytics hides PII by default."""
    # 1. Volunteer creates dog with guardian_phone -> 201, phone omitted from response
    create_res = client.post(
        "/api/dogs",
        json={
            "area_id": sample_area.id,
            "sex": "female",
            "guardian_name": "Sunita Devi",
            "guardian_phone": "+91-98765-11111",
            "capture_address": "22 Temple Road",
            "latitude": 19.076,
            "longitude": 72.8777,
        },
        headers=volunteer_headers,
    )
    assert create_res.status_code == 201
    created = create_res.get_json()
    dog_id = created["id"]
    assert "guardian_phone" not in created

    # 2. Admin reads dog -> guardian_phone IS present
    adm_get = client.get(f"/api/dogs/{dog_id}", headers=admin_headers)
    assert adm_get.status_code == 200
    assert adm_get.get_json()["guardian_phone"] == "+91-98765-11111"

    # 3. Volunteer updates dog while sending a different guardian_phone -> ignored & omitted
    vol_patch = client.patch(
        f"/api/dogs/{dog_id}",
        json={
            "landmark": "Near Temple Gate",
            "guardian_phone": "+91-00000-99999",
        },
        headers=volunteer_headers,
    )
    assert vol_patch.status_code == 200
    assert vol_patch.get_json()["landmark"] == "Near Temple Gate"
    assert "guardian_phone" not in vol_patch.get_json()

    # Admin still sees the original guardian_phone unchanged
    adm_after = client.get(f"/api/dogs/{dog_id}", headers=admin_headers)
    assert adm_after.get_json()["guardian_phone"] == "+91-98765-11111"

    # 4. Analytics export excludes personal fields by default
    an_default = client.get("/api/analytics/export?format=json", headers=admin_headers)
    assert an_default.status_code == 200
    row_default = next(i for i in an_default.get_json()["items"] if i["dog_id"] == dog_id)
    for field in (
        "guardian_name",
        "guardian_phone",
        "capture_address",
        "latitude",
        "longitude",
        "maps_url",
    ):
        assert field not in row_default

    # 5. Analytics export includes personal fields only when include_personal=true
    an_personal = client.get(
        "/api/analytics/export?format=json&include_personal=true",
        headers=admin_headers,
    )
    assert an_personal.status_code == 200
    row_personal = next(i for i in an_personal.get_json()["items"] if i["dog_id"] == dog_id)
    assert row_personal["guardian_name"] == "Sunita Devi"
    assert row_personal["guardian_phone"] == "+91-98765-11111"
    assert row_personal["capture_address"] == "22 Temple Road"
    assert row_personal["latitude"] == 19.076
    assert row_personal["longitude"] == 72.8777
