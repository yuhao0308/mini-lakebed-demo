"""
Tests for price range normalization in inventory search.

These tests verify that reversed price ranges are handled correctly:
- "between $35,000 and $20,000" should normalize to min=20000, max=35000
- Works with various formats: $35k, 35000, $35,000
- Does not break single-bound queries (under/over)
"""

import pytest
from app.services.llm import (
    _extract_inventory_entities,
    _fallback_classification,
    Intent
)


class TestPriceRangeNormalization:
    """Tests for price range normalization."""

    def test_between_normal_order(self):
        """Test 'between $20,000 and $35,000' (normal order)."""
        entities = _extract_inventory_entities("Show me SUVs between $20,000 and $35,000")
        assert entities.min_price == 20000.0
        assert entities.max_price == 35000.0
        assert entities.body_style == "suv"

    def test_between_reversed_order(self):
        """Test 'between $35,000 and $20,000' (reversed order) - THE BUG FIX."""
        entities = _extract_inventory_entities("Show me SUVs between $35,000 and $20,000")
        # Should normalize: min=20000, max=35000
        assert entities.min_price == 20000.0
        assert entities.max_price == 35000.0
        assert entities.body_style == "suv"

    def test_between_reversed_with_k_suffix(self):
        """Test 'between 35k and 20k' (reversed with k suffix)."""
        entities = _extract_inventory_entities("Find trucks between 35k and 20k")
        assert entities.min_price == 20000.0
        assert entities.max_price == 35000.0
        assert entities.body_style == "truck"

    def test_between_mixed_formats(self):
        """Test 'between $35,000 and 20000' (mixed formats, reversed)."""
        entities = _extract_inventory_entities("SUVs between $35,000 and 20000")
        assert entities.min_price == 20000.0
        assert entities.max_price == 35000.0

    def test_from_to_reversed(self):
        """Test 'from $40,000 to $25,000' (reversed)."""
        entities = _extract_inventory_entities("Show me sedans from $40,000 to $25,000")
        assert entities.min_price == 25000.0
        assert entities.max_price == 40000.0
        assert entities.body_style == "sedan"

    def test_dash_range_reversed(self):
        """Test '$40k-$25k' dash format (reversed)."""
        entities = _extract_inventory_entities("Trucks $40k-$25k")
        assert entities.min_price == 25000.0
        assert entities.max_price == 40000.0

    def test_dash_range_normal(self):
        """Test '$25k-$40k' dash format (normal order)."""
        entities = _extract_inventory_entities("SUVs $25k-$40k")
        assert entities.min_price == 25000.0
        assert entities.max_price == 40000.0

    def test_same_price_both_bounds(self):
        """Test when both prices are the same."""
        entities = _extract_inventory_entities("Cars between $30,000 and $30,000")
        assert entities.min_price == 30000.0
        assert entities.max_price == 30000.0


class TestSingleBoundPrices:
    """Tests for single-bound price queries (under/over) - should not be affected."""

    def test_under_price(self):
        """Test 'under $30,000'."""
        entities = _extract_inventory_entities("Show me SUVs under $30,000")
        assert entities.min_price is None
        assert entities.max_price == 30000.0
        assert entities.body_style == "suv"

    def test_over_price(self):
        """Test 'over $25,000'."""
        entities = _extract_inventory_entities("Trucks over $25,000")
        assert entities.min_price == 25000.0
        assert entities.max_price is None
        assert entities.body_style == "truck"

    def test_less_than_price(self):
        """Test 'less than $40k'."""
        entities = _extract_inventory_entities("Sedans less than $40k")
        assert entities.min_price is None
        assert entities.max_price == 40000.0

    def test_more_than_price(self):
        """Test 'more than 20k'."""
        entities = _extract_inventory_entities("Coupes more than 20k")
        assert entities.min_price == 20000.0
        assert entities.max_price is None

    def test_up_to_price(self):
        """Test 'up to $35,000'."""
        entities = _extract_inventory_entities("SUVs up to $35,000")
        assert entities.max_price == 35000.0

    def test_starting_at_price(self):
        """Test 'starting at $28,000'."""
        entities = _extract_inventory_entities("Trucks starting at $28,000")
        assert entities.min_price == 28000.0


class TestFallbackClassificationWithReversedRange:
    """Test that fallback classification works with reversed ranges."""

    def test_reversed_range_returns_inventory_search(self):
        """Reversed range should still classify as INVENTORY_SEARCH."""
        result = _fallback_classification("Show me SUVs between $35,000 and $20,000")
        assert result.intent == Intent.INVENTORY_SEARCH
        assert result.entities.min_price == 20000.0
        assert result.entities.max_price == 35000.0
        assert result.entities.body_style == "suv"

    def test_normal_range_returns_inventory_search(self):
        """Normal range should classify as INVENTORY_SEARCH."""
        result = _fallback_classification("Show me trucks between $20,000 and $35,000")
        assert result.intent == Intent.INVENTORY_SEARCH
        assert result.entities.min_price == 20000.0
        assert result.entities.max_price == 35000.0


class TestPriceParsingEdgeCases:
    """Test edge cases in price parsing."""

    def test_with_commas_and_dollar_signs(self):
        """Test '$35,000 and $20,000' with full formatting."""
        entities = _extract_inventory_entities("between $35,000 and $20,000")
        assert entities.min_price == 20000.0
        assert entities.max_price == 35000.0

    def test_without_dollar_signs(self):
        """Test '35000 and 20000' without dollar signs."""
        entities = _extract_inventory_entities("between 35000 and 20000")
        assert entities.min_price == 20000.0
        assert entities.max_price == 35000.0

    def test_k_suffix_lowercase(self):
        """Test '35k and 20k' with lowercase k."""
        entities = _extract_inventory_entities("between 35k and 20k")
        assert entities.min_price == 20000.0
        assert entities.max_price == 35000.0

    def test_thousand_suffix(self):
        """Test '35 thousand and 20 thousand'."""
        entities = _extract_inventory_entities("between 35 thousand and 20 thousand")
        assert entities.min_price == 20000.0
        assert entities.max_price == 35000.0

    def test_large_price_difference(self):
        """Test with large price difference."""
        entities = _extract_inventory_entities("between $100,000 and $15,000")
        assert entities.min_price == 15000.0
        assert entities.max_price == 100000.0

    def test_small_prices(self):
        """Test with small prices (used cars)."""
        entities = _extract_inventory_entities("between $8,000 and $5,000")
        assert entities.min_price == 5000.0
        assert entities.max_price == 8000.0
