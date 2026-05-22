"""Tests for vehicle service — retire, unretire."""

import pytest

from app.exceptions import BusinessRuleError
from app.services import vehicle as vehicle_service


class TestRetireVehicle:
    def test_retire_success(self, db, vehicle):
        result = vehicle_service.retire_vehicle(db, vehicle.id, "End of life")
        assert result.status == "retired"
        assert result.retirement_reason == "End of life"

    def test_retire_already_retired(self, db, vehicle):
        vehicle_service.retire_vehicle(db, vehicle.id, "Old")
        with pytest.raises(BusinessRuleError, match="already retired"):
            vehicle_service.retire_vehicle(db, vehicle.id, "Again")


class TestUnretireVehicle:
    def test_unretire_success(self, db, vehicle):
        vehicle_service.retire_vehicle(db, vehicle.id, "Old")
        result = vehicle_service.unretire_vehicle(db, vehicle.id)
        assert result.status == "active"
        assert result.retirement_reason is None

    def test_unretire_active_fails(self, db, vehicle):
        with pytest.raises(BusinessRuleError, match="not retired"):
            vehicle_service.unretire_vehicle(db, vehicle.id)
