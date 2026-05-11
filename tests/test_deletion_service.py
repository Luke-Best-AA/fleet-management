"""Tests for deletion service layer."""

from datetime import date

import pytest

from app.exceptions import (
    AuthorisationError,
    BusinessRuleError,
    NotFoundError,
)
from app.services import deletion as deletion_service
from app.services import maintenance as maint_service
from app.services import mileage as mileage_service


class TestGetDeletionRequestById:
    def test_returns_request(self, db, vehicle, standard_user, admin_user, category):
        maint_rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            standard_user.id,
            date.today(),
            10000,
            user_role="standard",
            user_vehicle_id=standard_user.id,
        )
        req = deletion_service.create_request(
            db,
            "maintenance_record",
            maint_rec.id,
            standard_user.id,
            "Please delete",
            user_role="standard",
            user_id=standard_user.id,
        )
        result = deletion_service.get_request_by_id(db, req.id)
        assert result.target_type == "maintenance_record"

    def test_raises_not_found(self, db):
        with pytest.raises(NotFoundError, match="Deletion request not found"):
            deletion_service.get_request_by_id(db, 9999)


class TestGetAllDeletionRequests:
    def test_returns_all(self, db, vehicle, standard_user, category):
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
        deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Delete it",
            user_role="standard",
            user_id=standard_user.id,
        )
        reqs = deletion_service.get_all_requests(db)
        assert len(reqs) == 1

    def test_filter_by_status(self, db, vehicle, standard_user, category):
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
        deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Delete it",
            user_role="standard",
            user_id=standard_user.id,
        )
        pending = deletion_service.get_all_requests(db, status="pending")
        assert len(pending) == 1
        approved = deletion_service.get_all_requests(db, status="approved")
        assert len(approved) == 0


class TestGetDeletionRequestsForUser:
    def test_returns_user_requests(self, db, vehicle, standard_user, admin_user, category):
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
        deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Delete",
            user_role="standard",
            user_id=standard_user.id,
        )
        user_reqs = deletion_service.get_requests_for_user(db, standard_user.id)
        assert len(user_reqs) == 1
        admin_reqs = deletion_service.get_requests_for_user(db, admin_user.id)
        assert len(admin_reqs) == 0


class TestCreateDeletionRequest:
    def test_create_for_maintenance_record(self, db, vehicle, standard_user, category):
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
        req = deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Wrong entry",
            user_role="standard",
            user_id=standard_user.id,
        )
        assert req.status == "pending"
        assert req.target_type == "maintenance_record"
        assert req.target_id == rec.id

    def test_create_for_mileage_record(self, db, vehicle, standard_user):
        rec = mileage_service.create_record(
            db,
            vehicle.id,
            standard_user.id,
            15000,
            user_role="standard",
            user_id=standard_user.id,
        )
        req = deletion_service.create_request(
            db,
            "mileage_record",
            rec.id,
            standard_user.id,
            "Incorrect reading",
            user_role="standard",
            user_id=standard_user.id,
        )
        assert req.target_type == "mileage_record"

    def test_nonexistent_target_fails(self, db, standard_user):
        with pytest.raises(BusinessRuleError, match="not found"):
            deletion_service.create_request(
                db,
                "maintenance_record",
                9999,
                standard_user.id,
                "Delete",
                user_role="standard",
                user_id=standard_user.id,
            )

    def test_already_deleted_target_fails(self, db, vehicle, standard_user, category):
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
        rec.is_deleted = True
        db.commit()
        with pytest.raises(BusinessRuleError, match="not found"):
            deletion_service.create_request(
                db,
                "maintenance_record",
                rec.id,
                standard_user.id,
                "Delete",
                user_role="standard",
                user_id=standard_user.id,
            )

    def test_standard_user_unassigned_vehicle_fails(self, db, vehicle, location, category):
        from app.services import user as user_service

        other = user_service.create_user(
            db,
            username="other_del",
            email="del@test.com",
            password="pass1234",
            first_name="O",
            last_name="D",
            location_id=location.id,
        )
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            vehicle.primary_driver_user_id,
            date.today(),
            10000,
            user_role="admin",
        )
        with pytest.raises(AuthorisationError, match="assigned vehicle"):
            deletion_service.create_request(
                db,
                "maintenance_record",
                rec.id,
                other.id,
                "Delete",
                user_role="standard",
                user_id=other.id,
            )

    def test_duplicate_pending_request_fails(self, db, vehicle, standard_user, category):
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
        deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "First",
            user_role="standard",
            user_id=standard_user.id,
        )
        with pytest.raises(BusinessRuleError, match="pending deletion request"):
            deletion_service.create_request(
                db,
                "maintenance_record",
                rec.id,
                standard_user.id,
                "Second",
                user_role="standard",
                user_id=standard_user.id,
            )

    def test_admin_can_request_any_record(self, db, vehicle, admin_user, category):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            admin_user.id,
            date.today(),
            10000,
            user_role="admin",
        )
        req = deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            admin_user.id,
            "Admin delete",
            user_role="admin",
        )
        assert req.status == "pending"

    def test_invalid_target_type_fails(self, db, standard_user):
        with pytest.raises(BusinessRuleError, match="not found"):
            deletion_service.create_request(
                db,
                "invalid_type",
                1,
                standard_user.id,
                "Delete",
                user_role="admin",
            )


class TestReviewDeletionRequest:
    def test_approve_deletes_maintenance_record(self, db, vehicle, standard_user, admin_user, category):
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
        req = deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Wrong",
            user_role="standard",
            user_id=standard_user.id,
        )
        deletion_service.review_request(db, req.id, admin_user.id, "approve")
        db.refresh(rec)
        assert rec.is_deleted is True
        db.refresh(req)
        assert req.status == "approved"
        assert req.reviewed_at is not None

    def test_approve_deletes_mileage_record_and_recalculates(self, db, vehicle, standard_user, admin_user):
        mileage_service.create_record(
            db,
            vehicle.id,
            standard_user.id,
            15000,
            user_role="standard",
            user_id=standard_user.id,
        )
        rec2 = mileage_service.create_record(
            db,
            vehicle.id,
            standard_user.id,
            20000,
            user_role="standard",
            user_id=standard_user.id,
        )
        req = deletion_service.create_request(
            db,
            "mileage_record",
            rec2.id,
            standard_user.id,
            "Wrong reading",
            user_role="standard",
            user_id=standard_user.id,
        )
        deletion_service.review_request(db, req.id, admin_user.id, "approve")
        db.refresh(rec2)
        assert rec2.is_deleted is True
        db.refresh(vehicle)
        assert vehicle.current_mileage == 15000

    def test_reject_keeps_record(self, db, vehicle, standard_user, admin_user, category):
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
        req = deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Delete",
            user_role="standard",
            user_id=standard_user.id,
        )
        deletion_service.review_request(db, req.id, admin_user.id, "reject", review_notes="No")
        db.refresh(rec)
        assert rec.is_deleted is False
        db.refresh(req)
        assert req.status == "rejected"
        assert req.review_notes == "No"

    def test_review_already_reviewed_fails(self, db, vehicle, standard_user, admin_user, category):
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
        req = deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Delete",
            user_role="standard",
            user_id=standard_user.id,
        )
        deletion_service.review_request(db, req.id, admin_user.id, "approve")
        with pytest.raises(BusinessRuleError, match="already been reviewed"):
            deletion_service.review_request(db, req.id, admin_user.id, "reject")
