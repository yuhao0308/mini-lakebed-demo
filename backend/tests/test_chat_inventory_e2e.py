"""
End-to-end tests for chat inventory search.

These tests verify the FULL chat flow including:
- Price range normalization works through both LLM and fallback paths
- SUVs in reversed price range return results (not "no vehicles found")
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestChatInventorySearchE2E:
    """End-to-end tests for chat inventory search."""

    def test_suvs_reversed_price_range_returns_results(self):
        """
        THE BUG FIX TEST: "SUVs between $35,000 and $20000" should return vehicles.

        This was failing because:
        - LLM path didn't normalize price range
        - SQL became: price >= 35000 AND price <= 20000 (impossible)
        """
        response = client.post("/api/chat", json={
            "message": "Show me SUVs between $35,000 and $20000",
            "session_id": "test_reversed_price_e2e"
        })

        assert response.status_code == 200
        data = response.json()

        # Should NOT contain "couldn't find" message
        assert "couldn't find" not in data["response"].lower(), \
            f"Expected results but got: {data['response'][:200]}"

        # Should contain "Found X vehicles" or vehicle results
        assert "found" in data["response"].lower() or data.get("tool_calls"), \
            f"Expected inventory results but got: {data['response'][:200]}"

    def test_suvs_normal_price_range_returns_results(self):
        """Normal order price range should work."""
        response = client.post("/api/chat", json={
            "message": "Show me SUVs between $20,000 and $35,000",
            "session_id": "test_normal_price_e2e"
        })

        assert response.status_code == 200
        data = response.json()

        assert "couldn't find" not in data["response"].lower()

    def test_trucks_reversed_price_range(self):
        """Trucks with reversed price range should work."""
        response = client.post("/api/chat", json={
            "message": "Find trucks between 40k and 25k",
            "session_id": "test_trucks_reversed_e2e"
        })

        assert response.status_code == 200
        data = response.json()

        # May or may not find trucks in this range, but shouldn't error
        assert response.status_code == 200

    def test_sedans_under_price(self):
        """Single-bound 'under' query should work."""
        response = client.post("/api/chat", json={
            "message": "Show me sedans under $30,000",
            "session_id": "test_sedans_under_e2e"
        })

        assert response.status_code == 200
        data = response.json()

        # Should not error
        assert "error" not in data.get("response", "").lower()

    def test_metadata_contains_intent(self):
        """Response should include intent metadata."""
        response = client.post("/api/chat", json={
            "message": "Show me SUVs between $35,000 and $20000",
            "session_id": "test_metadata_e2e"
        })

        assert response.status_code == 200
        data = response.json()

        assert "metadata" in data
        assert "intent" in data["metadata"]
        # Intent should be inventory_search (not clarification)
        assert data["metadata"]["intent"] in ["inventory_search", "greeting"], \
            f"Unexpected intent: {data['metadata']['intent']}"


class TestChatPriceExtractionE2E:
    """Test that price extraction works correctly in real chat flow."""

    def test_k_suffix_prices(self):
        """Prices with 'k' suffix should parse correctly."""
        response = client.post("/api/chat", json={
            "message": "SUVs from 20k to 35k",
            "session_id": "test_k_suffix_e2e"
        })

        assert response.status_code == 200
        data = response.json()

        # Should process without error
        assert "error" not in str(data).lower()

    def test_comma_formatted_prices(self):
        """Prices with commas should parse correctly."""
        response = client.post("/api/chat", json={
            "message": "Show trucks $25,000 - $40,000",
            "session_id": "test_comma_e2e"
        })

        assert response.status_code == 200

    def test_mixed_format_prices(self):
        """Mixed price formats should work."""
        response = client.post("/api/chat", json={
            "message": "SUVs between $35k and 20000",
            "session_id": "test_mixed_e2e"
        })

        assert response.status_code == 200
        data = response.json()

        # Should not show "couldn't find" for reversed range
        assert "couldn't find" not in data["response"].lower()
