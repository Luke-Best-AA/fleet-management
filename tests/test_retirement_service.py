"""Tests for retirement service layer."""

import pytest

from app.exceptions import (
    AuthorisationError,
    BusinessRuleError,
    NotFoundError,
)
from app.services import retirement as retirement_service
from app.services import user as user_service


class TestGetRetirementRequestById:
    def test_returns_request(self, db, vehicle, admin_user):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            admin_user.id,
            "Old vehicle",
            user_role="admin",
        )
        result = retirement_service.get_request_by_id(db, req.id)
        assert result.reason == "Old vehicle"

    def test_raises_not_found(self, db):
        with pytest.raises(NotFoundError, match="Retirement request not found"):
            retirement_service.get_request_by_id(db, 9999)


class TestGetAllRequests:
    def test_returns_all(self, db, vehicle, admin_user):
        retirement_service.create_request(
            db,
            vehicle.id,
            admin_user.id,
            "Reason",
            user_role="admin",
        )
        requests = retirement_service.get_all_requests(db)
        assert len(requests) == 1

    def test_filter_by_status(self, db, vehicle, admin_user):
        retirement_service.create_request(
            db,
            vehicle.id,
            admin_user.id,
            "Reason",
            user_role="admin",
        )
        pending = retirement_service.get_all_requests(db, status="pending")
        assert len(pending) == 1
        approved = retirement_service.get_all_requests(db, status="approved")
        assert len(approved) == 0


class TestGetRequestsForUser:
    def test_returns_user_requests(self, db, vehicle, standard_user, admin_user):
        retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "Please retire",
            user_role="standard",
            user_id=standard_user.id,
        )
        user_reqs = retirement_service.get_requests_for_user(db, standard_user.id)
        assert len(user_reqs) == 1
        admin_reqs = retirement_service.get_requests_for_user(db, admin_user.id)
        assert len(admin_reqs) == 0


class TestCreateRetirementRequest:
    def test_standard_user_creates_request(self, db, vehicle, standard_user):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "Vehicle is too old",
            user_role="standard",
            user_id=standard_user.id,
        )
        assert req.status == "pending"
        db.refresh(vehicle)
        assert vehicle.status == "pending_retirement"

    def test_admin_creates_request(self, db, vehicle, admin_user):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            admin_user.id,
            "Decommission",
            user_role="admin",
        )
        assert req.status == "pending"

    def test_retired_vehicle_fails(self, db, vehicle, admin_user):
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="active"):
            retirement_service.create_request(
                db,
                vehicle.id,
                admin_user.id,
                "Already retired",
                user_role="admin",
            )

    def test_pending_retirement_vehicle_fails(self, db, vehicle, admin_user):
        vehicle.status = "pending_retirement"
        db.commit()
        with pytest.raises(BusinessRuleError, match="active"):
            retirement_service.create_request(
                db,
                vehicle.id,
                admin_user.id,
                "Already pending",
                user_role="admin",
            )

    def test_duplicate_pending_request_fails(self, db, vehicle, admin_user):
        retirement_service.create_request(
            db,
            vehicle.id,
            admin_user.id,
            "First request",
            user_role="admin",
        )
        # Reset status to active to test the pending check directly
        vehicle.status = "active"
        db.commit()
        with pytest.raises(BusinessRuleError, match="pending"):
            retirement_service.create_request(
                db,
                vehicle.id,
                admin_user.id,
                "Second request",
                user_role="admin",
            )

    def test_standard_user_unassigned_vehicle_fails(self, db, vehicle, location):
        other = user_service.create_user(
            db,
            username="other_retire",
            email="retire@test.com",
            password="pass1234",
            first_name="O",
            last_name="R",
            location_id=location.id,
        )
        with pytest.raises(AuthorisationError):
            retirement_service.create_request(
                db,
                vehicle.id,
                other.id,
                "Not my vehicle",
                user_role="standard",
                user_id=other.id,
            )

    def test_deleted_vehicle_fails(self, db, vehicle, admin_user):
        vehicle.is_deleted = True
        db.commit()
        with pytest.raises(BusinessRuleError, match="not found"):
            retirement_service.create_request(
                db,
                vehicle.id,
                admin_user.id,
                "Deleted",
                user_role="admin",
            )


class TestReviewRetirementRequest:
    def test_approve_retires_vehicle(self, db, vehicle, standard_user, admin_user):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "Too old",
            user_role="standard",
            user_id=standard_user.id,
        )
        retirement_service.review_request(db, req.id, admin_user.id, "approve")
        db.refresh(vehicle)
        assert vehicle.status == "retired"
        db.refresh(req)
        assert req.status == "approved"
        assert req.reviewed_by_user_id == admin_user.id
        assert req.reviewed_at is not None

    def test_approve_sets_retirement_reason(self, db, vehicle, standard_user, admin_user):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "High mileage",
            user_role="standard",
            user_id=standard_user.id,
        )
        retirement_service.review_request(db, req.id, admin_user.id, "approve")
        db.refresh(vehicle)
        assert vehicle.retirement_reason == "High mileage"

    def test_reject_restores_active(self, db, vehicle, standard_user, admin_user):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "Want to retire",
            user_role="standard",
            user_id=standard_user.id,
        )
        assert vehicle.status == "pending_retirement"
        retirement_service.review_request(db, req.id, admin_user.id, "reject")
        db.refresh(vehicle)
        assert vehicle.status == "active"
        db.refresh(req)
        assert req.status == "rejected"

    def test_reject_with_review_notes(self, db, vehicle, standard_user, admin_user):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "Want to retire",
            user_role="standard",
            user_id=standard_user.id,
        )
        retirement_service.review_request(
            db,
            req.id,
            admin_user.id,
            "reject",
            review_notes="Still in good condition",
        )
        db.refresh(req)
        assert req.review_notes == "Still in good condition"

    def test_review_already_reviewed_fails(self, db, vehicle, standard_user, admin_user):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "Retire please",
            user_role="standard",
            user_id=standard_user.id,
        )
        retirement_service.review_request(db, req.id, admin_user.id, "approve")
        with pytest.raises(BusinessRuleError, match="already been reviewed"):
            retirement_service.review_request(db, req.id, admin_user.id, "reject")


class TestRetireVehicleDirectly:
    def test_admin_retire_directly(self, db, vehicle, admin_user):
        result = retirement_service.retire_vehicle_directly(
            db,
            vehicle.id,
            "Decommissioned",
            admin_user.id,
        )
        assert result.status == "retired"
        assert result.retirement_reason == "Decommissioned"

    def test_retire_non_active_fails(self, db, vehicle, admin_user):
        vehicle.status = "retired"
        db.commit()
        with pytest.raises(BusinessRuleError, match="active"):
            retirement_service.retire_vehicle_directly(
                db,
                vehicle.id,
                "Already retired",
                admin_user.id,
            )

    def test_retire_deleted_vehicle_fails(self, db, vehicle, admin_user):
        vehicle.is_deleted = True
        db.commit()
        with pytest.raises(BusinessRuleError, match="not found"):
            retirement_service.retire_vehicle_directly(
                db,
                vehicle.id,
                "Deleted",
                admin_user.id,
            )
