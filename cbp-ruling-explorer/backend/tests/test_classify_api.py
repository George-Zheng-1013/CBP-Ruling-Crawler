def test_classify_validation(client):
    response = client.post(
        "/api/classify",
        json={"product_name": "Cable", "description": "too short"},
    )
    assert response.status_code == 400


def test_classify_response_and_references(client, monkeypatch):
    from app.routers import classify

    monkeypatch.setattr(
        classify._service,
        "classify",
        lambda product: {
            "product_profile": "Copper battery cable with connectors",
            "primary": {
                "hts_code": "8544.42.90.00",
                "description": "Other electric conductors",
                "parent_path": "Insulated wire",
                "confidence": "high",
                "basis": ["Function and connector configuration match the cited ruling."],
            },
            "alternatives": [],
            "references": [
                {
                    "ruling_no": "N12345",
                    "subject": "Test ruling",
                    "ruling_date": "2024-01-01",
                    "year": 2024,
                    "hs_codes": ["8544.42.9000"],
                    "status": "active",
                    "detail_url": "https://rulings.cbp.gov/ruling/N12345",
                    "section": "FACTS",
                    "excerpt": "A copper cable fitted with connectors.",
                    "similarities": ["same function"],
                    "differences": [],
                }
            ],
            "missing_information": [],
            "warnings": [],
            "hts_version": "2026 Revision 11",
            "disclaimer": "Not binding.",
        },
    )
    response = client.post(
        "/api/classify",
        json={
            "product_name": "Battery cable",
            "description": "Copper cable fitted with connectors for a battery.",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["primary"]["hts_code"] == "8544.42.90.00"
    assert data["references"][0]["ruling_no"] == "N12345"
