"""Public unauthenticated dog endpoint allow-list & soft-delete tests (Step B10)."""

from datetime import date


def test_public_endpoint_allowlist_and_soft_delete(
    client, admin_headers, volunteer_headers, sample_area
):
    """Public endpoint returns strictly allow-listed fields and 404 after soft delete."""
    dog_res = client.post(
        "/api/dogs",
        json={
            "area_id": sample_area.id,
            "sex": "male",
            "guardian_name": "Private Guardian",
            "guardian_phone": "+91-99887-76655",
            "capture_address": "Private Address 101",
            "landmark": "Private Landmark",
            "latitude": 19.123456,
            "longitude": 72.654321,
            "medical_conditions": "Private Medical Condition",
            "medical_history": "Private Medical History",
        },
        headers=volunteer_headers,
    )
    assert dog_res.status_code == 201
    dog = dog_res.get_json()
    dog_id = dog["id"]
    token = dog["public_token"]

    # Add a surgery case and vaccination
    today = date.today().isoformat()
    assert (
        client.post(
            f"/api/dogs/{dog_id}/cases",
            json={"pickup_date": today, "surgery_date": today},
            headers=volunteer_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/dogs/{dog_id}/vaccinations",
            json={"vaccine_name": "Anti-Rabies", "date_given": today},
            headers=volunteer_headers,
        ).status_code
        == 201
    )

    # Unauthenticated request -> 200 with ONLY the 8 allow-listed keys
    pub_res = client.get(f"/api/public/dogs/{token}")
    assert pub_res.status_code == 200
    data = pub_res.get_json()

    allowed_keys = {
        "dog_code",
        "area_name",
        "area_color_name",
        "area_color_hex",
        "primary_photo_url",
        "sterilized",
        "latest_vaccination",
        "ngo_contact",
    }
    assert set(data.keys()) == allowed_keys
    assert data["sterilized"] is True
    assert data["latest_vaccination"] == {"vaccine_name": "Anti-Rabies", "date_given": today}

    for forbidden in (
        "guardian_name",
        "guardian_phone",
        "capture_address",
        "landmark",
        "latitude",
        "longitude",
        "maps_url",
        "medical_conditions",
        "medical_history",
    ):
        assert forbidden not in data

    # Soft-delete the dog -> public endpoint must return 404
    assert client.delete(f"/api/dogs/{dog_id}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/public/dogs/{token}").status_code == 404
