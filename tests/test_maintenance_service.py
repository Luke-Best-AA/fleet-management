"""Tests for maintenance service layer."""

from datetime import date
from decimal import Decimal

import pytest

from app.exceptions import (
    AuthorisationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)
from app.services import maintenance as maint_service


class TestGetCategoryById:
    def test_returns_category(self, db, category):
        result = maint_service.get_category_by_id(db, category.id)
        assert result.name == "Test Category"

    def test_raises_not_found(self, db):
        with pytest.raises(NotFoundError, match="Please select a valid maintenance category"):
            maint_service.get_category_by_id(db, 9999)

    def test_raises_not_found_for_deleted(self, db, category):
        category.is_deleted = True
        db.commit()
        with pytest.raises(NotFoundError):
            maint_service.get_category_by_id(db, category.id)


class TestGetAllCategories:
    def test_returns_all(self, db, category, category_with_notes):
        categories = maint_service.get_all_categories(db)
        assert len(categories) == 2

    def test_active_only_filter(self, db, category):
        inactive = maint_service.create_category(db, "Inactive Cat", requires_notes=False)
        inactive.is_active = False
        db.commit()
        active = maint_service.get_all_categories(db, active_only=True)
        assert len(active) == 1
        assert active[0].id == category.id

    def test_excludes_deleted(self, db, category):
        category.is_deleted = True
        db.commit()
        categories = maint_service.get_all_categories(db)
        assert len(categories) == 0


class TestCreateCategory:
    def test_create_basic(self, db):
        cat = maint_service.create_category(db, "Oil Change")
        assert cat.id is not None
        assert cat.name == "Oil Change"
        assert cat.requires_notes is False

    def test_create_with_notes_required(self, db):
        cat = maint_service.create_category(db, "Inspection", requires_notes=True)
        assert cat.requires_notes is True

    def test_create_with_description(self, db):
        cat = maint_service.create_category(db, "Tyre Change", description="Replacing tyres")
        assert cat.description == "Replacing tyres"

    def test_duplicate_name_fails(self, db, category):
        with pytest.raises(ConflictError, match="name already in use"):
            maint_service.create_category(db, "Test Category")


class TestUpdateCategory:
    def test_update_name(self, db, category):
        updated = maint_service.update_category(db, category.id, "Renamed Category")
        assert updated.name == "Renamed Category"

    def test_update_requires_notes(self, db, category):
        updated = maint_service.update_category(db, category.id, "Test Category", requires_notes=True)
        assert updated.requires_notes is True

    def test_update_duplicate_name_fails(self, db, category, category_with_notes):
        with pytest.raises(ConflictError, match="name already in use"):
            maint_service.update_category(db, category.id, "Notes Required")

    def test_update_same_name_ok(self, db, category):
        updated = maint_service.update_category(db, category.id, "Test Category")
        assert updated.name == "Test Category"

    def test_update_is_active(self, db, category):
        updated = maint_service.update_category(db, category.id, "Test Category", is_active=False)
        assert updated.is_active is False


class TestSoftDeleteCategory:
    def test_soft_delete(self, db, category):
        maint_service.soft_delete_category(db, category.id)
        db.refresh(category)
        assert category.is_deleted is True

    def test_soft_delete_nonexistent_raises(self, db):
        with pytest.raises(NotFoundError):
            maint_service.soft_delete_category(db, 9999)


class TestGetMaintenanceRecordById:
    def test_returns_record(self, db, vehicle, standard_user, category):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            standard_user.id,
            date.today(),
            10000,
            user_role="standard",
            user_vehicle_id=standard_user.id,
        )
        result = maint_service.get_record_by_id(db, rec.id)
        assert result.vehicle_id == vehicle.id

    def test_raises_not_found(self, db):
        with pytest.raises(NotFoundError, match="Maintenance record not found"):
            maint_service.get_record_by_id(db, 9999)


class TestCreateMaintenanceRecord:
    def test_create_basic(self, db, vehicle, standard_user, category):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            standard_user.id,
            date.today(),
            10000,
            user_role="standard",
            user_vehicle_id=standard_user.id,
        )
        assert rec.id is not None
        assert rec.vehicle_id == vehicle.id
        assert rec.category_id == category.id

    def test_create_with_notes(self, db, vehicle, standard_user, category):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            standard_user.id,
            date.today(),
            10000,
            notes="Changed oil and filter",
            user_role="standard",
            user_vehicle_id=standard_user.id,
        )
        assert rec.notes == "Changed oil and filter"

    def test_create_with_cost(self, db, vehicle, admin_user, category):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            admin_user.id,
            date.today(),
            10000,
            cost=Decimal("150.50"),
            user_role="admin",
        )
        assert rec.cost == Decimal("150.50")

    def test_notes_required_enforced(self, db, vehicle, standard_user, category_with_notes):
        with pytest.raises(BusinessRuleError, match="Notes are required"):
            maint_service.create_record(
                db,
                vehicle.id,
                category_with_notes.id,
                standard_user.id,
                date.today(),
                10000,
                notes="",
                user_role="standard",
                user_vehicle_id=standard_user.id,
            )

    def test_notes_required_with_notes_succeeds(self, db, vehicle, standard_user, category_with_notes):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category_with_notes.id,
            standard_user.id,
            date.today(),
            10000,
            notes="Detailed inspection notes",
            user_role="standard",
            user_vehicle_id=standard_user.id,
        )
        assert rec.notes == "Detailed inspection notes"

    def test_retired_vehicle_fails(self, db, vehicle, admin_user, category):
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="retired"):
            maint_service.create_record(
                db,
                vehicle.id,
                category.id,
                admin_user.id,
                date.today(),
                10000,
                user_role="admin",
            )

    def test_deleted_vehicle_fails(self, db, vehicle, admin_user, category):
        vehicle.is_deleted = True
        db.commit()
        with pytest.raises(BusinessRuleError, match="not found"):
            maint_service.create_record(
                db,
                vehicle.id,
                category.id,
                admin_user.id,
                date.today(),
                10000,
                user_role="admin",
            )

    def test_inactive_category_fails(self, db, vehicle, admin_user, category):
        category.is_active = False
        db.commit()
        with pytest.raises(BusinessRuleError, match="not active"):
            maint_service.create_record(
                db,
                vehicle.id,
                category.id,
                admin_user.id,
                date.today(),
                10000,
                user_role="admin",
            )

    def test_standard_user_unassigned_vehicle_fails(self, db, vehicle, location, category):
        from app.services import user as user_service

        other = user_service.create_user(
            db,
            username="other_maint",
            email="othermaint@test.com",
            password="password123",
            first_name="Other",
            last_name="Driver",
            location_id=location.id,
        )
        with pytest.raises(AuthorisationError, match="assigned vehicle"):
            maint_service.create_record(
                db,
                vehicle.id,
                category.id,
                other.id,
                date.today(),
                10000,
                user_role="standard",
                user_vehicle_id=other.id,
            )

    def test_admin_can_log_any_vehicle(self, db, vehicle, admin_user, category):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            admin_user.id,
            date.today(),
            10000,
            user_role="admin",
        )
        assert rec.id is not None

    def test_notes_whitespace_stripped(self, db, vehicle, admin_user, category):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            admin_user.id,
            date.today(),
            10000,
            notes="  spaced  ",
            user_role="admin",
        )
        assert rec.notes == "spaced"

    def test_empty_notes_stored_as_none(self, db, vehicle, admin_user, category):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            admin_user.id,
            date.today(),
            10000,
            notes="",
            user_role="admin",
        )
        assert rec.notes is None


class TestUpdateMaintenanceRecord:
    def test_update_record(self, db, vehicle, admin_user, category):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            admin_user.id,
            date.today(),
            10000,
            user_role="admin",
        )
        updated = maint_service.update_record(
            db,
            rec.id,
            category.id,
            date(2025, 1, 15),
            12000,
            notes="Updated",
        )
        assert updated.mileage_at_time == 12000
        assert updated.notes == "Updated"

    def test_update_notes_required_enforced(self, db, vehicle, admin_user, category_with_notes):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category_with_notes.id,
            admin_user.id,
            date.today(),
            10000,
            notes="Initial notes",
            user_role="admin",
        )
        with pytest.raises(BusinessRuleError, match="Notes are required"):
            maint_service.update_record(
                db,
                rec.id,
                category_with_notes.id,
                date.today(),
                12000,
                notes="",
            )

    def test_update_retired_vehicle_fails(self, db, vehicle, admin_user, category):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            admin_user.id,
            date.today(),
            10000,
            user_role="admin",
        )
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="retired"):
            maint_service.update_record(
                db,
                rec.id,
                category.id,
                date.today(),
                12000,
            )


class TestGetMaintenanceRecords:
    def test_get_records_for_vehicle(self, db, vehicle, admin_user, category):
        maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            admin_user.id,
            date.today(),
            10000,
            user_role="admin",
        )
        maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            admin_user.id,
            date.today(),
            12000,
            user_role="admin",
        )
        records = maint_service.get_records_for_vehicle(db, vehicle.id)
        assert len(records) == 2

    def test_get_all_records(self, db, vehicle, admin_user, category):
        maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            admin_user.id,
            date.today(),
            10000,
            user_role="admin",
        )
        records = maint_service.get_all_records(db)
        assert len(records) == 1
