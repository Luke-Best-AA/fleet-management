"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import ChangePasswordSchema, LoginSchema, RegisterSchema
from app.schemas.location import LocationCreateSchema
from app.schemas.maintenance import (
    MaintenanceCategoryCreateSchema,
    MaintenanceRecordCreateSchema,
)
from app.schemas.mileage import MileageCreateSchema
from app.schemas.requests import (
    DeletionRequestCreateSchema,
    RetirementRequestCreateSchema,
    RetirementRequestReviewSchema,
)
from app.schemas.user import UserCreateSchema
from app.schemas.vehicle import VehicleCreateSchema


class TestVehicleSchema:
    def test_valid_current_format(self):
        s = VehicleCreateSchema(
            registration_number="AB12 CDE",
            fleet_reference="FLT-001",
            vehicle_type="roadside_van",
            make="Ford",
            model="Transit",
            year=2023,
            location_id=1,
        )
        assert s.registration_number == "AB12 CDE"

    def test_valid_prefix_format(self):
        s = VehicleCreateSchema(
            registration_number="A123 ABC",
            fleet_reference="FLT-001",
            vehicle_type="roadside_van",
            make="Ford",
            model="Transit",
            year=2023,
            location_id=1,
        )
        assert s.registration_number == "A123 ABC"

    def test_invalid_registration(self):
        with pytest.raises(ValidationError) as exc_info:
            VehicleCreateSchema(
                registration_number="INVALID123",
                fleet_reference="FLT-001",
                vehicle_type="roadside_van",
                make="Ford",
                model="Transit",
                year=2023,
                location_id=1,
            )
        assert "registration" in str(exc_info.value).lower()

    def test_empty_registration(self):
        with pytest.raises(ValidationError):
            VehicleCreateSchema(
                registration_number="",
                fleet_reference="FLT-001",
                vehicle_type="roadside_van",
                make="Ford",
                model="Transit",
                year=2023,
                location_id=1,
            )

    def test_invalid_vehicle_type(self):
        with pytest.raises(ValidationError) as exc_info:
            VehicleCreateSchema(
                registration_number="AB12 CDE",
                fleet_reference="FLT-001",
                vehicle_type="helicopter",
                make="Ford",
                model="Transit",
                year=2023,
                location_id=1,
            )
        assert "vehicle type" in str(exc_info.value).lower()

    def test_year_too_low(self):
        with pytest.raises(ValidationError):
            VehicleCreateSchema(
                registration_number="AB12 CDE",
                fleet_reference="FLT-001",
                vehicle_type="roadside_van",
                make="Ford",
                model="Transit",
                year=1800,
                location_id=1,
            )

    def test_year_too_high(self):
        with pytest.raises(ValidationError):
            VehicleCreateSchema(
                registration_number="AB12 CDE",
                fleet_reference="FLT-001",
                vehicle_type="roadside_van",
                make="Ford",
                model="Transit",
                year=2200,
                location_id=1,
            )

    def test_negative_mileage(self):
        with pytest.raises(ValidationError):
            VehicleCreateSchema(
                registration_number="AB12 CDE",
                fleet_reference="FLT-001",
                vehicle_type="roadside_van",
                make="Ford",
                model="Transit",
                year=2023,
                location_id=1,
                current_mileage=-100,
            )

    def test_registration_case_insensitive(self):
        s = VehicleCreateSchema(
            registration_number="ab12 cde",
            fleet_reference="FLT-001",
            vehicle_type="roadside_van",
            make="Ford",
            model="Transit",
            year=2023,
            location_id=1,
        )
        assert s.registration_number == "AB12 CDE"

    def test_empty_make_fails(self):
        with pytest.raises(ValidationError):
            VehicleCreateSchema(
                registration_number="AB12 CDE",
                fleet_reference="FLT-001",
                vehicle_type="roadside_van",
                make="",
                model="Transit",
                year=2023,
                location_id=1,
            )


class TestRegisterSchema:
    def test_valid_registration(self):
        s = RegisterSchema(
            username="testuser",
            email="test@example.com",
            password="password123",
            password_confirm="password123",
            first_name="Test",
            last_name="User",
        )
        assert s.username == "testuser"

    def test_password_mismatch(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="testuser",
                email="test@example.com",
                password="password123",
                password_confirm="different123",
                first_name="Test",
                last_name="User",
            )
        assert "match" in str(exc_info.value).lower()

    def test_short_password(self):
        with pytest.raises(ValidationError):
            RegisterSchema(
                username="testuser",
                email="test@example.com",
                password="short",
                password_confirm="short",
                first_name="Test",
                last_name="User",
            )

    def test_short_username(self):
        with pytest.raises(ValidationError):
            RegisterSchema(
                username="ab",
                email="test@example.com",
                password="password123",
                password_confirm="password123",
                first_name="Test",
                last_name="User",
            )


class TestLocationSchema:
    def test_valid_location(self):
        s = LocationCreateSchema(name="Test Depot", code="TST")
        assert s.name == "Test Depot"

    def test_empty_name_fails(self):
        with pytest.raises(ValidationError):
            LocationCreateSchema(name="", code="TST")

    def test_empty_code_fails(self):
        with pytest.raises(ValidationError):
            LocationCreateSchema(name="Test Depot", code="")


class TestMaintenanceSchemas:
    def test_valid_category(self):
        s = MaintenanceCategoryCreateSchema(name="Oil Change")
        assert s.name == "Oil Change"

    def test_valid_record(self):
        from datetime import date

        s = MaintenanceRecordCreateSchema(
            vehicle_id=1,
            category_id=1,
            maintenance_date=date.today(),
            mileage_at_time=10000,
        )
        assert s.vehicle_id == 1

    def test_negative_mileage_fails(self):
        from datetime import date

        with pytest.raises(ValidationError):
            MaintenanceRecordCreateSchema(
                vehicle_id=1,
                category_id=1,
                maintenance_date=date.today(),
                mileage_at_time=-100,
            )


class TestMileageSchema:
    def test_valid_mileage(self):
        s = MileageCreateSchema(vehicle_id=1, reading_value=15000)
        assert s.reading_value == 15000

    def test_negative_reading_fails(self):
        with pytest.raises(ValidationError):
            MileageCreateSchema(vehicle_id=1, reading_value=-100)


class TestRequestSchemas:
    def test_valid_retirement_request(self):
        s = RetirementRequestCreateSchema(
            vehicle_id=1,
            reason="Vehicle is too old to keep running",
        )
        assert s.vehicle_id == 1

    def test_retirement_reason_too_short(self):
        with pytest.raises(ValidationError):
            RetirementRequestCreateSchema(vehicle_id=1, reason="Short")

    def test_valid_retirement_review(self):
        s = RetirementRequestReviewSchema(action="approve", review_notes="OK")
        assert s.action == "approve"

    def test_invalid_review_action(self):
        with pytest.raises(ValidationError):
            RetirementRequestReviewSchema(action="cancel", review_notes="")

    def test_valid_deletion_request(self):
        s = DeletionRequestCreateSchema(
            target_type="maintenance_record",
            target_id=1,
            reason="Wrong entry",
        )
        assert s.target_type == "maintenance_record"

    def test_invalid_deletion_target_type(self):
        with pytest.raises(ValidationError):
            DeletionRequestCreateSchema(
                target_type="invalid_type",
                target_id=1,
                reason="Delete",
            )


class TestUserSchema:
    def test_valid_user(self):
        s = UserCreateSchema(
            username="testuser",
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
        )
        assert s.username == "testuser"

    def test_short_username_fails(self):
        with pytest.raises(ValidationError):
            UserCreateSchema(
                username="ab",
                email="test@example.com",
                password="password123",
                first_name="Test",
                last_name="User",
            )


# --- Coverage tests merged from test_schema_validators.py ---


class TestLoginSchemaValidation:
    def test_empty_username(self):
        with pytest.raises(ValidationError) as exc_info:
            LoginSchema(username="   ", password="pass")
        assert "Username is required" in str(exc_info.value)

    def test_empty_password(self):
        with pytest.raises(ValidationError) as exc_info:
            LoginSchema(username="user", password="")
        assert "Password is required" in str(exc_info.value)

    def test_valid(self):
        schema = LoginSchema(username="user", password="pass")
        assert schema.username == "user"


class TestRegisterSchemaValidation:
    def test_invalid_role(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="user",
                email="test@test.com",
                password="password123",
                password_confirm="password123",
                first_name="Test",
                last_name="User",
                role="superadmin",
            )
        assert "Role must be standard or admin" in str(exc_info.value)

    def test_short_username(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="ab",
                email="test@test.com",
                password="password123",
                password_confirm="password123",
                first_name="Test",
                last_name="User",
            )
        assert "between 3 and 100" in str(exc_info.value)

    def test_empty_username(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="   ",
                email="test@test.com",
                password="password123",
                password_confirm="password123",
                first_name="Test",
                last_name="User",
            )
        assert "Username is required" in str(exc_info.value)

    def test_short_password(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="validuser",
                email="test@test.com",
                password="short",
                password_confirm="short",
                first_name="Test",
                last_name="User",
            )
        assert "at least 8 characters" in str(exc_info.value)

    def test_password_mismatch(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="validuser",
                email="test@test.com",
                password="password123",
                password_confirm="different123",
                first_name="Test",
                last_name="User",
            )
        assert "do not match" in str(exc_info.value)

    def test_empty_first_name(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="validuser",
                email="test@test.com",
                password="password123",
                password_confirm="password123",
                first_name="   ",
                last_name="User",
            )
        assert "First name is required" in str(exc_info.value)

    def test_long_first_name(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="validuser",
                email="test@test.com",
                password="password123",
                password_confirm="password123",
                first_name="A" * 101,
                last_name="User",
            )
        assert "100 characters" in str(exc_info.value)

    def test_empty_last_name(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="validuser",
                email="test@test.com",
                password="password123",
                password_confirm="password123",
                first_name="Test",
                last_name="   ",
            )
        assert "Last name is required" in str(exc_info.value)

    def test_long_last_name(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="validuser",
                email="test@test.com",
                password="password123",
                password_confirm="password123",
                first_name="Test",
                last_name="A" * 101,
            )
        assert "100 characters" in str(exc_info.value)

    def test_long_employee_number(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                username="validuser",
                email="test@test.com",
                password="password123",
                password_confirm="password123",
                first_name="Test",
                last_name="User",
                employee_number="X" * 51,
            )
        assert "50 characters" in str(exc_info.value)

    def test_valid_employee_number(self):
        schema = RegisterSchema(
            username="validuser",
            email="test@test.com",
            password="password123",
            password_confirm="password123",
            first_name="Test",
            last_name="User",
            employee_number="EMP001",
        )
        assert schema.employee_number == "EMP001"


class TestChangePasswordSchemaValidation:
    def test_empty_current_password(self):
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordSchema(
                current_password="",
                new_password="newpass123",
                new_password_confirm="newpass123",
            )
        assert "Current password is required" in str(exc_info.value)

    def test_short_new_password(self):
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordSchema(
                current_password="oldpass",
                new_password="short",
                new_password_confirm="short",
            )
        assert "at least 8 characters" in str(exc_info.value)

    def test_new_password_mismatch(self):
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordSchema(
                current_password="oldpass",
                new_password="newpass123",
                new_password_confirm="different",
            )
        assert "do not match" in str(exc_info.value)

    def test_valid(self):
        ChangePasswordSchema(
            current_password="oldpass",
            new_password="newpass123",
            new_password_confirm="newpass123",
        )
