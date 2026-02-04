"""Tests for CostTracker class."""

import pytest

from aorchestra.models.cost import CostRecord, CostTracker


class TestCostTracker:
    """Tests for CostTracker functionality."""

    def test_init_empty(self):
        """Test CostTracker initializes with empty records."""
        tracker = CostTracker()
        assert tracker.get_delegation_count() == 0
        assert tracker.get_total_cost() == 0.0
        assert tracker.get_total_tokens() == 0
        assert tracker.get_records() == []

    def test_track_single_record(self):
        """Test tracking a single cost record."""
        tracker = CostTracker()
        record = CostRecord(
            model_name="glm-4.7",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.0015,
        )
        tracker.track(record)

        assert tracker.get_delegation_count() == 1
        assert tracker.get_total_cost() == 0.0015
        assert tracker.get_total_tokens() == 150

    def test_track_multiple_records(self):
        """Test tracking multiple cost records."""
        tracker = CostTracker()
        records = [
            CostRecord(
                model_name="glm-4-flash",
                prompt_tokens=50,
                completion_tokens=25,
                total_tokens=75,
                estimated_cost_usd=0.0001,
            ),
            CostRecord(
                model_name="glm-4.7",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=0.0015,
            ),
            CostRecord(
                model_name="glm-4-plus",
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                estimated_cost_usd=0.01,
            ),
        ]

        for record in records:
            tracker.track(record)

        assert tracker.get_delegation_count() == 3
        assert tracker.get_total_cost() == pytest.approx(0.0116)
        assert tracker.get_total_tokens() == 525

    def test_get_total_cost(self):
        """Test get_total_cost returns sum of all costs."""
        tracker = CostTracker()
        tracker.track(
            CostRecord(
                model_name="test",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.001,
            )
        )
        tracker.track(
            CostRecord(
                model_name="test",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.002,
            )
        )

        assert tracker.get_total_cost() == 0.003

    def test_get_total_cost_empty(self):
        """Test get_total_cost returns 0.0 for empty tracker."""
        tracker = CostTracker()
        assert tracker.get_total_cost() == 0.0

    def test_get_total_tokens(self):
        """Test get_total_tokens returns sum of all tokens."""
        tracker = CostTracker()
        tracker.track(
            CostRecord(
                model_name="test",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=100,
                estimated_cost_usd=0.0,
            )
        )
        tracker.track(
            CostRecord(
                model_name="test",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=200,
                estimated_cost_usd=0.0,
            )
        )

        assert tracker.get_total_tokens() == 300

    def test_get_total_tokens_empty(self):
        """Test get_total_tokens returns 0 for empty tracker."""
        tracker = CostTracker()
        assert tracker.get_total_tokens() == 0

    def test_get_delegation_count(self):
        """Test get_delegation_count returns number of records."""
        tracker = CostTracker()
        assert tracker.get_delegation_count() == 0

        for i in range(5):
            tracker.track(
                CostRecord(
                    model_name="test",
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    estimated_cost_usd=0.0,
                )
            )

        assert tracker.get_delegation_count() == 5

    def test_get_summary(self):
        """Test get_summary returns comprehensive breakdown."""
        tracker = CostTracker()
        tracker.track(
            CostRecord(
                model_name="glm-4-flash",
                prompt_tokens=50,
                completion_tokens=25,
                total_tokens=75,
                estimated_cost_usd=0.0001,
            )
        )
        tracker.track(
            CostRecord(
                model_name="glm-4-flash",
                prompt_tokens=30,
                completion_tokens=20,
                total_tokens=50,
                estimated_cost_usd=0.00007,
            )
        )
        tracker.track(
            CostRecord(
                model_name="glm-4.7",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=0.0015,
            )
        )

        summary = tracker.get_summary()

        assert summary["total_cost_usd"] == pytest.approx(0.00167)
        assert summary["total_tokens"] == 275
        assert summary["delegation_count"] == 3
        assert "model_breakdown" in summary

        # Check model breakdown
        assert "glm-4-flash" in summary["model_breakdown"]
        assert summary["model_breakdown"]["glm-4-flash"]["calls"] == 2
        assert summary["model_breakdown"]["glm-4-flash"]["tokens"] == 125
        assert summary["model_breakdown"]["glm-4-flash"]["cost_usd"] == pytest.approx(0.00017)

        assert "glm-4.7" in summary["model_breakdown"]
        assert summary["model_breakdown"]["glm-4.7"]["calls"] == 1
        assert summary["model_breakdown"]["glm-4.7"]["tokens"] == 150
        assert summary["model_breakdown"]["glm-4.7"]["cost_usd"] == 0.0015

    def test_get_summary_empty(self):
        """Test get_summary returns empty breakdown for empty tracker."""
        tracker = CostTracker()
        summary = tracker.get_summary()

        assert summary["total_cost_usd"] == 0.0
        assert summary["total_tokens"] == 0
        assert summary["delegation_count"] == 0
        assert summary["model_breakdown"] == {}

    def test_reset(self):
        """Test reset clears all records."""
        tracker = CostTracker()
        tracker.track(
            CostRecord(
                model_name="test",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=0.0015,
            )
        )
        tracker.track(
            CostRecord(
                model_name="test",
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                estimated_cost_usd=0.003,
            )
        )

        assert tracker.get_delegation_count() == 2

        tracker.reset()

        assert tracker.get_delegation_count() == 0
        assert tracker.get_total_cost() == 0.0
        assert tracker.get_total_tokens() == 0
        assert tracker.get_records() == []

    def test_get_records(self):
        """Test get_records returns a copy of records."""
        tracker = CostTracker()
        record1 = CostRecord(
            model_name="test",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.0015,
        )
        record2 = CostRecord(
            model_name="test",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            estimated_cost_usd=0.003,
        )

        tracker.track(record1)
        tracker.track(record2)

        records = tracker.get_records()
        assert len(records) == 2
        assert records[0].model_name == "test"

        # Modify returned list should not affect tracker
        records.append(record1)
        assert tracker.get_delegation_count() == 2  # Still 2

        # Note: Pydantic models are mutable, so modifying record fields will affect the tracker
        # This is expected behavior - get_records() returns a shallow copy of the list
        # but the records themselves are references

    def test_get_records_empty(self):
        """Test get_records returns empty list for empty tracker."""
        tracker = CostTracker()
        assert tracker.get_records() == []

    def test_edge_case_zero_cost(self):
        """Test handling of zero cost records."""
        tracker = CostTracker()
        tracker.track(
            CostRecord(
                model_name="test",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.0,
            )
        )

        assert tracker.get_total_cost() == 0.0
        assert tracker.get_total_tokens() == 0

    def test_multiple_same_model(self):
        """Test model_breakdown aggregates correctly for same model."""
        tracker = CostTracker()
        for i in range(3):
            tracker.track(
                CostRecord(
                    model_name="glm-4.7",
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    estimated_cost_usd=0.001,
                )
            )

        summary = tracker.get_summary()
        breakdown = summary["model_breakdown"]["glm-4.7"]

        assert breakdown["calls"] == 3
        assert breakdown["tokens"] == 450
        assert breakdown["cost_usd"] == 0.003
