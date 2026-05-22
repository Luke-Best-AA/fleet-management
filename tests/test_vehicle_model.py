"""Tests for Vehicle model mileage_source property (lines 71-84)."""

from datetime import date

from app.models.maintenance import MaintenanceRecord
from app.models.mileage import MileageRecord
from app.models.vehicle import Vehicle


class TestMileageSourceProperty:
    def test_returns_none_when_zero_mileage(self, db, location):
        v = Vehicle(
            registration_number="MS01 AAA",
            fleet_reference="FLT-MS-001",
            vehicle_type="patrol_van",
            make="Ford",
            model="Transit",
            year=2023,
            current_mileage=0,
            location_id=location.id,
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        assert v.mileage_source is None

    def test_returns_mileage_record_source(self, db, location, standard_user):
        v = Vehicle(
            registration_number="MS02 BBB",
            fleet_reference="FLT-MS-002",
            vehicle_type="patrol_van",
            make="Ford",
            model="Transit",
            year=2023,
            current_mileage=5000,
            location_id=location.id,
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        rec = MileageRecord(
            vehicle_id=v.id,
            recorded_by_user_id=standard_user.id,
            reading_value=5000,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

        db.refresh(v)
        result = v.mileage_source
        assert result is not None
        assert result["type"] == "mileage_record"
        assert result["id"] == rec.id

    def test_returns_maintenance_record_source(self, db, location, admin_user, category):
        v = Vehicle(
            registration_number="MS03 CCC",
            fleet_reference="FLT-MS-003",
            vehicle_type="patrol_van",
            make="Ford",
            model="Transit",
            year=2023,
            current_mileage=8000,
            location_id=location.id,
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        rec = MaintenanceRecord(
            vehicle_id=v.id,
            category_id=category.id,
            logged_by_user_id=admin_user.id,
            maintenance_date=date.today(),
            mileage_at_time=8000,
            notes="Service",
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

        db.refresh(v)
        result = v.mileage_source
        assert result is not None
        assert result["type"] == "maintenance_record"
        assert result["id"] == rec.id

    def test_returns_none_when_no_matching_record(self, db, location):
        v = Vehicle(
            registration_number="MS04 DDD",
            fleet_reference="FLT-MS-004",
            vehicle_type="patrol_van",
            make="Ford",
            model="Transit",
            year=2023,
            current_mileage=9999,
            location_id=location.id,
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        assert v.mileage_source is None
