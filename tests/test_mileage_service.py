"""Tests for mileage service layer."""

import pytest

from app.exceptions import (
    AuthorisationError,
    BusinessRuleError,
    NotFoundError,
)
from app.services import mileage as mileage_service


class TestGetMileageRecordById:
    def test_returns_record(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            15000,
            user_role="admin",
            user_id=admin_user.id,
        )
        result = mileage_service.get_record_by_id(db, rec.id)
        assert result.reading_value == 15000

    def test_raises_not_found(self, db):
        with pytest.raises(NotFoundError, match="Mileage record not found"):
            mileage_service.get_record_by_id(db, 9999)

    def test_raises_not_found_for_deleted(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            15000,
            user_role="admin",
            user_id=admin_user.id,
        )
        rec.is_deleted = True
        db.commit()
        with pytest.raises(NotFoundError):
            mileage_service.get_record_by_id(db, rec.id)


class TestGetRecordsForVehicle:
    def test_returns_records_for_vehicle(self, db, vehicle, admin_user):
        mileage_service.create_record(db, vehicle.id, admin_user.id, 15000, user_role="admin", user_id=admin_user.id)
        mileage_service.create_record(db, vehicle.id, admin_user.id, 20000, user_role="admin", user_id=admin_user.id)
        records = mileage_service.get_records_for_vehicle(db, vehicle.id)
        assert len(records) == 2

    def test_excludes_deleted(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db, vehicle.id, admin_user.id, 15000, user_role="admin", user_id=admin_user.id
        )
        rec.is_deleted = True
        db.commit()
        records = mileage_service.get_records_for_vehicle(db, vehicle.id)
        assert len(records) == 0


class TestCreateMileageRecord:
    def test_standard_user_higher_mileage(self, db, vehicle, standard_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            standard_user.id,
            15000,
            user_role="standard",
            user_id=standard_user.id,
        )
        assert rec.reading_value == 15000
        db.refresh(vehicle)
        assert vehicle.current_mileage == 15000

    def test_standard_user_lower_mileage_fails(self, db, vehicle, standard_user):
        with pytest.raises(BusinessRuleError, match="at least"):
            mileage_service.create_record(
                db,
                vehicle.id,
                standard_user.id,
                5000,
                user_role="standard",
                user_id=standard_user.id,
            )

    def test_standard_user_unassigned_vehicle_fails(self, db, vehicle, location):
        from app.services import user as user_service

        other = user_service.create_user(
            db,
            username="other_driver",
            email="other@test.com",
            password="password123",
            first_name="Other",
            last_name="Driver",
            location_id=location.id,
        )
        with pytest.raises(AuthorisationError):
            mileage_service.create_record(
                db,
                vehicle.id,
                other.id,
                20000,
                user_role="standard",
                user_id=other.id,
            )

    def test_standard_user_override_ignored(self, db, vehicle, standard_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            standard_user.id,
            15000,
            is_admin_override=True,
            override_reason="Trying override",
            user_role="standard",
            user_id=standard_user.id,
        )
        assert rec.is_admin_override is False

    def test_admin_higher_mileage(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            20000,
            user_role="admin",
            user_id=admin_user.id,
        )
        assert rec.reading_value == 20000
        db.refresh(vehicle)
        assert vehicle.current_mileage == 20000

    def test_admin_lower_without_override_fails(self, db, vehicle, admin_user):
        with pytest.raises(BusinessRuleError, match="below current mileage"):
            mileage_service.create_record(
                db,
                vehicle.id,
                admin_user.id,
                5000,
                user_role="admin",
                user_id=admin_user.id,
            )

    def test_admin_override_without_reason_fails(self, db, vehicle, admin_user):
        with pytest.raises(BusinessRuleError, match="reason"):
            mileage_service.create_record(
                db,
                vehicle.id,
                admin_user.id,
                5000,
                is_admin_override=True,
                override_reason="",
                user_role="admin",
                user_id=admin_user.id,
            )

    def test_admin_override_with_reason_succeeds(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            5000,
            is_admin_override=True,
            override_reason="Odometer correction",
            user_role="admin",
            user_id=admin_user.id,
        )
        assert rec.is_admin_override is True
        assert rec.override_reason == "Odometer correction"

    def test_retired_vehicle_fails(self, db, vehicle, admin_user):
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="retired"):
            mileage_service.create_record(
                db,
                vehicle.id,
                admin_user.id,
                20000,
                user_role="admin",
                user_id=admin_user.id,
            )

    def test_deleted_vehicle_fails(self, db, vehicle, admin_user):
        vehicle.is_deleted = True
        db.commit()
        with pytest.raises(BusinessRuleError, match="Please select a vehicle"):
            mileage_service.create_record(
                db,
                vehicle.id,
                admin_user.id,
                20000,
                user_role="admin",
                user_id=admin_user.id,
            )

    def test_updates_current_mileage_on_higher(self, db, vehicle, admin_user):
        mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            25000,
            user_role="admin",
            user_id=admin_user.id,
        )
        db.refresh(vehicle)
        assert vehicle.current_mileage == 25000

    def test_admin_override_recalculates_mileage(self, db, vehicle, admin_user):
        mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            20000,
            user_role="admin",
            user_id=admin_user.id,
        )
        mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            5000,
            is_admin_override=True,
            override_reason="Reset",
            user_role="admin",
            user_id=admin_user.id,
        )
        db.refresh(vehicle)
        # Max of all readings (20000, 5000) = 20000
        assert vehicle.current_mileage == 20000


class TestUpdateMileageRecord:
    def test_update_reading(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            15000,
            user_role="admin",
            user_id=admin_user.id,
        )
        updated = mileage_service.update_record(db, rec.id, 18000)
        assert updated.reading_value == 18000

    def test_update_override_without_reason_fails(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            15000,
            user_role="admin",
            user_id=admin_user.id,
        )
        with pytest.raises(BusinessRuleError, match="reason"):
            mileage_service.update_record(db, rec.id, 5000, is_admin_override=True, override_reason="")

    def test_update_changes_reading_value(self, db, vehicle, admin_user):
        mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            15000,
            user_role="admin",
            user_id=admin_user.id,
        )
        rec2 = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            20000,
            user_role="admin",
            user_id=admin_user.id,
        )
        mileage_service.update_record(db, rec2.id, 25000)
        db.refresh(rec2)
        assert rec2.reading_value == 25000

    def test_update_retired_vehicle_fails(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            15000,
            user_role="admin",
            user_id=admin_user.id,
        )
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="retired"):
            mileage_service.update_record(db, rec.id, 18000)


class TestSoftDeleteMileageRecord:
    def test_soft_delete(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            15000,
            user_role="admin",
            user_id=admin_user.id,
        )
        mileage_service.soft_delete_record(db, rec.id)
        db.refresh(rec)
        assert rec.is_deleted is True

    def test_soft_delete_recalculates_mileage(self, db, vehicle, admin_user):
        mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            15000,
            user_role="admin",
            user_id=admin_user.id,
        )
        rec2 = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            25000,
            user_role="admin",
            user_id=admin_user.id,
        )
        mileage_service.soft_delete_record(db, rec2.id)
        db.refresh(vehicle)
        assert vehicle.current_mileage == 15000

    def test_soft_delete_all_records_resets_to_zero(self, db, vehicle, admin_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            admin_user.id,
            15000,
            user_role="admin",
            user_id=admin_user.id,
        )
        mileage_service.soft_delete_record(db, rec.id)
        db.refresh(vehicle)
        assert vehicle.current_mileage == 0

    def test_soft_delete_nonexistent_raises(self, db):
        with pytest.raises(NotFoundError):
            mileage_service.soft_delete_record(db, 9999)
