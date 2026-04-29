"""Tests for business rule enforcement."""
import pytest
from datetime import date

from app.exceptions import (
    AuthorisationError,
    BusinessRuleError,
    ConflictError,
)
from app.services import maintenance as maint_service
from app.services import mileage as mileage_service
from app.services import retirement as retirement_service
from app.services import user as user_service
from app.services import vehicle as vehicle_service


class TestUserRules:
    def test_username_must_be_unique(self, db, admin_user):
        with pytest.raises(ConflictError, match="Username already taken"):
            user_service.create_user(
                db, username="testadmin", email="other@x.com",
                password="pass1234", first_name="A", last_name="B",
            )

    def test_email_must_be_unique(self, db, admin_user):
        with pytest.raises(ConflictError, match="Email already in use"):
            user_service.create_user(
                db, username="other", email="admin@test.com",
                password="pass1234", first_name="A", last_name="B",
            )

    def test_only_admin_can_create_admin(self, db):
        with pytest.raises(AuthorisationError):
            user_service.create_user(
                db, username="sneakyadmin", email="sneak@x.com",
                password="pass1234", first_name="S", last_name="A",
                role="admin", requesting_user_role="standard",
            )

    def test_admin_can_create_admin(self, db):
        u = user_service.create_user(
            db, username="newadmin", email="na@x.com",
            password="pass1234", first_name="N", last_name="A",
            role="admin", requesting_user_role="admin",
        )
        assert u.role == "admin"


class TestVehicleRules:
    def test_retired_vehicle_cannot_be_edited(self, db, vehicle):
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="Retired"):
            vehicle_service.update_vehicle(
                db, vehicle.id, "XX11 YYY", "FLT-TEST-001",
                "roadside_van", "Ford", "Transit", 2023, vehicle.location_id,
            )

    def test_primary_driver_must_be_standard(self, db, vehicle, admin_user):
        with pytest.raises(BusinessRuleError, match="standard user"):
            vehicle_service.update_vehicle(
                db, vehicle.id, "XX11 YYY", "FLT-TEST-001",
                "roadside_van", "Ford", "Transit", 2023,
                vehicle.location_id, primary_driver_user_id=admin_user.id,
            )

    def test_registration_unique(self, db, vehicle, location):
        with pytest.raises(ConflictError, match="Registration"):
            vehicle_service.create_vehicle(
                db, "XX11 YYY", "FLT-NEW", "patrol_van",
                "Vauxhall", "Vivaro", 2023, location.id,
            )


class TestMileageRules:
    def test_standard_user_mileage_must_not_decrease(self, db, vehicle, standard_user):
        with pytest.raises(BusinessRuleError, match="at least"):
            mileage_service.create_record(
                db, vehicle.id, standard_user.id, 5000,
                user_role="standard", user_id=standard_user.id,
            )

    def test_standard_user_can_add_higher_mileage(self, db, vehicle, standard_user):
        rec = mileage_service.create_record(
            db, vehicle.id, standard_user.id, 15000,
            user_role="standard", user_id=standard_user.id,
        )
        assert rec.reading_value == 15000

    def test_admin_override_requires_reason(self, db, vehicle, admin_user):
        with pytest.raises(BusinessRuleError, match="reason"):
            mileage_service.create_record(
                db, vehicle.id, admin_user.id, 5000,
                is_admin_override=True, override_reason="",
                user_role="admin", user_id=admin_user.id,
            )

    def test_admin_override_with_reason_succeeds(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db, vehicle.id, admin_user.id, 5000,
            is_admin_override=True, override_reason="Correcting odometer error",
            user_role="admin", user_id=admin_user.id,
        )
        assert rec.is_admin_override is True

    def test_retired_vehicle_cannot_receive_mileage(self, db, vehicle, admin_user):
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="retired"):
            mileage_service.create_record(
                db, vehicle.id, admin_user.id, 20000,
                user_role="admin", user_id=admin_user.id,
            )

    def test_standard_user_cannot_add_to_unassigned_vehicle(self, db, vehicle, location):
        other_user = user_service.create_user(
            db, username="other", email="other@x.com",
            password="pass1234", first_name="O", last_name="U",
            location_id=location.id,
        )
        with pytest.raises(AuthorisationError):
            mileage_service.create_record(
                db, vehicle.id, other_user.id, 20000,
                user_role="standard", user_id=other_user.id,
            )


class TestMaintenanceRules:
    def test_requires_notes_enforced(self, db, vehicle, standard_user, category_with_notes):
        with pytest.raises(BusinessRuleError, match="Notes are required"):
            maint_service.create_record(
                db, vehicle.id, category_with_notes.id, standard_user.id,
                date.today(), 10000, notes="",
                user_role="standard", user_vehicle_id=standard_user.id,
            )

    def test_retired_vehicle_cannot_receive_maintenance(self, db, vehicle, admin_user, category):
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="retired"):
            maint_service.create_record(
                db, vehicle.id, category.id, admin_user.id,
                date.today(), 10000, user_role="admin",
            )


class TestRetirementRules:
    def test_only_active_vehicle_can_be_retired(self, db, vehicle, admin_user):
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="active"):
            retirement_service.create_request(
                db, vehicle.id, admin_user.id, "Old vehicle",
                user_role="admin",
            )

    def test_only_one_pending_request(self, db, vehicle, admin_user):
        retirement_service.create_request(
            db, vehicle.id, admin_user.id, "First request for retirement",
            user_role="admin",
        )
        # Vehicle is now pending_retirement, need another active vehicle
        # But this also tests the pending check
        with pytest.raises(BusinessRuleError, match="pending"):
            # Reset status to active to test the pending check directly
            vehicle.status = "active"
            db.commit()
            retirement_service.create_request(
                db, vehicle.id, admin_user.id, "Second request for retirement",
                user_role="admin",
            )

    def test_standard_user_can_only_retire_assigned_vehicle(self, db, vehicle, location):
        other = user_service.create_user(
            db, username="other2", email="other2@x.com",
            password="pass1234", first_name="O", last_name="U",
            location_id=location.id,
        )
        with pytest.raises(AuthorisationError):
            retirement_service.create_request(
                db, vehicle.id, other.id, "Want to retire this vehicle",
                user_role="standard", user_id=other.id,
            )

    def test_approve_retires_vehicle(self, db, vehicle, standard_user, admin_user):
        req = retirement_service.create_request(
            db, vehicle.id, standard_user.id, "Vehicle is too old to keep",
            user_role="standard", user_id=standard_user.id,
        )
        retirement_service.review_request(db, req.id, admin_user.id, "approve")
        db.refresh(vehicle)
        assert vehicle.status == "retired"
        db.refresh(req)
        assert req.status == "approved"
