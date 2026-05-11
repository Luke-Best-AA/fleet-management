"""Tests for vehicle service layer."""

import pytest

from app.exceptions import (
    AuthorisationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)
from app.services import vehicle as vehicle_service


class TestGetVehicleById:
    def test_returns_vehicle(self, db, vehicle):
        result = vehicle_service.get_vehicle_by_id(db, vehicle.id)
        assert result.id == vehicle.id
        assert result.registration_number == "XX11 YYY"

    def test_raises_not_found_for_missing(self, db):
        with pytest.raises(NotFoundError, match="Vehicle not found"):
            vehicle_service.get_vehicle_by_id(db, 9999)

    def test_raises_not_found_for_deleted(self, db, vehicle):
        vehicle.is_deleted = True
        db.commit()
        with pytest.raises(NotFoundError, match="Vehicle not found"):
            vehicle_service.get_vehicle_by_id(db, vehicle.id)


class TestGetAllVehicles:
    def test_returns_all_non_deleted(self, db, vehicle, location):
        vehicle_service.create_vehicle(
            db,
            "AB12 CDE",
            "FLT-002",
            "patrol_van",
            "Vauxhall",
            "Vivaro",
            2022,
            location.id,
        )
        vehicles = vehicle_service.get_all_vehicles(db)
        assert len(vehicles) == 2

    def test_excludes_deleted(self, db, vehicle):
        vehicle.is_deleted = True
        db.commit()
        vehicles = vehicle_service.get_all_vehicles(db)
        assert len(vehicles) == 0

    def test_ordered_by_registration(self, db, location):
        vehicle_service.create_vehicle(db, "ZZ99 ZZZ", "FLT-Z", "patrol_van", "Ford", "Transit", 2023, location.id)
        vehicle_service.create_vehicle(db, "AA11 AAA", "FLT-A", "roadside_van", "Ford", "Transit", 2023, location.id)
        vehicles = vehicle_service.get_all_vehicles(db)
        assert vehicles[0].registration_number == "AA11 AAA"
        assert vehicles[1].registration_number == "ZZ99 ZZZ"


class TestGetVehiclesForUser:
    def test_returns_only_assigned_vehicles(self, db, vehicle, standard_user, location):
        # vehicle is assigned to standard_user
        vehicle_service.create_vehicle(
            db,
            "AB12 CDE",
            "FLT-UNAS",
            "patrol_van",
            "Vauxhall",
            "Vivaro",
            2022,
            location.id,
        )
        vehicles = vehicle_service.get_vehicles_for_user(db, standard_user.id)
        assert len(vehicles) == 1
        assert vehicles[0].id == vehicle.id

    def test_returns_empty_for_no_vehicles(self, db, admin_user):
        vehicles = vehicle_service.get_vehicles_for_user(db, admin_user.id)
        assert vehicles == []


class TestCheckVehicleAccess:
    def test_admin_can_access_any(self, db, vehicle):
        user = {"id": 999, "role": "admin"}
        vehicle_service.check_vehicle_access(vehicle, user)  # Should not raise

    def test_standard_user_can_access_assigned(self, db, vehicle, standard_user):
        user = {"id": standard_user.id, "role": "standard"}
        vehicle_service.check_vehicle_access(vehicle, user)  # Should not raise

    def test_standard_user_cannot_access_unassigned(self, db, vehicle):
        user = {"id": 9999, "role": "standard"}
        with pytest.raises(AuthorisationError, match="assigned vehicle"):
            vehicle_service.check_vehicle_access(vehicle, user)


class TestCreateVehicle:
    def test_create_success(self, db, location):
        v = vehicle_service.create_vehicle(
            db,
            "AB12 CDE",
            "FLT-NEW",
            "roadside_van",
            "Ford",
            "Transit",
            2023,
            location.id,
        )
        assert v.id is not None
        assert v.registration_number == "AB12 CDE"
        assert v.current_mileage == 0

    def test_create_with_driver(self, db, location, standard_user):
        v = vehicle_service.create_vehicle(
            db,
            "AB12 CDE",
            "FLT-NEW",
            "roadside_van",
            "Ford",
            "Transit",
            2023,
            location.id,
            primary_driver_user_id=standard_user.id,
        )
        assert v.primary_driver_user_id == standard_user.id

    def test_duplicate_registration_fails(self, db, vehicle, location):
        with pytest.raises(ConflictError, match="Registration"):
            vehicle_service.create_vehicle(
                db,
                "XX11 YYY",
                "FLT-DUP",
                "patrol_van",
                "Vauxhall",
                "Vivaro",
                2023,
                location.id,
            )

    def test_duplicate_fleet_reference_fails(self, db, vehicle, location):
        with pytest.raises(ConflictError, match="Fleet reference"):
            vehicle_service.create_vehicle(
                db,
                "AB12 CDE",
                "FLT-TEST-001",
                "patrol_van",
                "Vauxhall",
                "Vivaro",
                2023,
                location.id,
            )

    def test_invalid_location_fails(self, db):
        with pytest.raises(BusinessRuleError, match="Location not found"):
            vehicle_service.create_vehicle(
                db,
                "AB12 CDE",
                "FLT-NEW",
                "roadside_van",
                "Ford",
                "Transit",
                2023,
                9999,
            )

    def test_deleted_location_fails(self, db, location):
        location.is_deleted = True
        db.commit()
        with pytest.raises(BusinessRuleError, match="Location not found"):
            vehicle_service.create_vehicle(
                db,
                "AB12 CDE",
                "FLT-NEW",
                "roadside_van",
                "Ford",
                "Transit",
                2023,
                location.id,
            )

    def test_admin_driver_fails(self, db, location, admin_user):
        with pytest.raises(BusinessRuleError, match="standard user"):
            vehicle_service.create_vehicle(
                db,
                "AB12 CDE",
                "FLT-NEW",
                "roadside_van",
                "Ford",
                "Transit",
                2023,
                location.id,
                primary_driver_user_id=admin_user.id,
            )

    def test_inactive_driver_fails(self, db, location, standard_user):
        standard_user.is_active = False
        db.commit()
        with pytest.raises(BusinessRuleError, match="active user"):
            vehicle_service.create_vehicle(
                db,
                "AB12 CDE",
                "FLT-NEW",
                "roadside_van",
                "Ford",
                "Transit",
                2023,
                location.id,
                primary_driver_user_id=standard_user.id,
            )

    def test_nonexistent_driver_fails(self, db, location):
        with pytest.raises(BusinessRuleError, match="Primary driver not found"):
            vehicle_service.create_vehicle(
                db,
                "AB12 CDE",
                "FLT-NEW",
                "roadside_van",
                "Ford",
                "Transit",
                2023,
                location.id,
                primary_driver_user_id=9999,
            )

    def test_create_with_mileage(self, db, location):
        v = vehicle_service.create_vehicle(
            db,
            "AB12 CDE",
            "FLT-NEW",
            "roadside_van",
            "Ford",
            "Transit",
            2023,
            location.id,
            current_mileage=5000,
        )
        assert v.current_mileage == 5000


class TestUpdateVehicle:
    def test_update_success(self, db, vehicle):
        updated = vehicle_service.update_vehicle(
            db,
            vehicle.id,
            "XX11 YYY",
            "FLT-TEST-001",
            "patrol_van",
            "Vauxhall",
            "Vivaro",
            2024,
            vehicle.location_id,
        )
        assert updated.vehicle_type == "patrol_van"
        assert updated.make == "Vauxhall"
        assert updated.year == 2024

    def test_update_retired_vehicle_fails(self, db, vehicle):
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="Retired"):
            vehicle_service.update_vehicle(
                db,
                vehicle.id,
                "XX11 YYY",
                "FLT-TEST-001",
                "roadside_van",
                "Ford",
                "Transit",
                2023,
                vehicle.location_id,
            )

    def test_update_duplicate_registration_fails(self, db, vehicle, location):
        vehicle_service.create_vehicle(
            db,
            "AB12 CDE",
            "FLT-OTHER",
            "patrol_van",
            "Ford",
            "Transit",
            2023,
            location.id,
        )
        with pytest.raises(ConflictError, match="Registration"):
            vehicle_service.update_vehicle(
                db,
                vehicle.id,
                "AB12 CDE",
                "FLT-TEST-001",
                "roadside_van",
                "Ford",
                "Transit",
                2023,
                vehicle.location_id,
            )

    def test_update_duplicate_fleet_ref_fails(self, db, vehicle, location):
        vehicle_service.create_vehicle(
            db,
            "AB12 CDE",
            "FLT-OTHER",
            "patrol_van",
            "Ford",
            "Transit",
            2023,
            location.id,
        )
        with pytest.raises(ConflictError, match="Fleet reference"):
            vehicle_service.update_vehicle(
                db,
                vehicle.id,
                "XX11 YYY",
                "FLT-OTHER",
                "roadside_van",
                "Ford",
                "Transit",
                2023,
                vehicle.location_id,
            )

    def test_update_same_registration_ok(self, db, vehicle):
        # Updating with its own registration should not conflict
        updated = vehicle_service.update_vehicle(
            db,
            vehicle.id,
            "XX11 YYY",
            "FLT-TEST-001",
            "roadside_van",
            "Ford",
            "Transit",
            2023,
            vehicle.location_id,
        )
        assert updated.registration_number == "XX11 YYY"


class TestSoftDeleteVehicle:
    def test_soft_delete(self, db, vehicle):
        vehicle_service.soft_delete_vehicle(db, vehicle.id)
        db.refresh(vehicle)
        assert vehicle.is_deleted is True

    def test_soft_delete_nonexistent_raises(self, db):
        with pytest.raises(NotFoundError):
            vehicle_service.soft_delete_vehicle(db, 9999)
