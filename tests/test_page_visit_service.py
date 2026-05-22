"""Tests for app.services.page_visit service."""

import pytest

from app.models.page_visit import PageVisit
from app.services import page_visit as pv_service


class TestRecordVisit:
    def test_creates_visit(self, db, admin_user):
        pv_service.record_visit(db, user_id=admin_user.id, path="/dashboard")
        visits = db.query(PageVisit).all()
        assert len(visits) == 1
        assert visits[0].path == "/dashboard"
        assert visits[0].method == "GET"

    def test_custom_method(self, db, admin_user):
        pv_service.record_visit(db, user_id=admin_user.id, path="/vehicles/create", method="POST")
        visit = db.query(PageVisit).first()
        assert visit.method == "POST"


class TestGetVisits:
    def test_returns_visits(self, db, admin_user):
        pv_service.record_visit(db, user_id=admin_user.id, path="/first")
        pv_service.record_visit(db, user_id=admin_user.id, path="/second")
        visits = pv_service.get_visits(db)
        assert len(visits) == 2
        paths = {v.path for v in visits}
        assert paths == {"/first", "/second"}

    def test_limit_and_offset(self, db, admin_user):
        for i in range(5):
            pv_service.record_visit(db, user_id=admin_user.id, path=f"/page{i}")
        page1 = pv_service.get_visits(db, limit=2, offset=0)
        assert len(page1) == 2
        page2 = pv_service.get_visits(db, limit=2, offset=2)
        assert len(page2) == 2

    def test_filter_by_user(self, db, admin_user, standard_user):
        pv_service.record_visit(db, user_id=admin_user.id, path="/admin")
        pv_service.record_visit(db, user_id=standard_user.id, path="/dash")
        visits = pv_service.get_visits(db, user_id=standard_user.id)
        assert len(visits) == 1
        assert visits[0].path == "/dash"

    def test_filter_by_days(self, db, admin_user):
        pv_service.record_visit(db, user_id=admin_user.id, path="/recent")
        visits = pv_service.get_visits(db, days=1)
        assert len(visits) == 1


class TestCountVisits:
    def test_total_count(self, db, admin_user):
        for _ in range(3):
            pv_service.record_visit(db, user_id=admin_user.id, path="/x")
        assert pv_service.count_visits(db) == 3

    def test_count_by_user(self, db, admin_user, standard_user):
        pv_service.record_visit(db, user_id=admin_user.id, path="/x")
        pv_service.record_visit(db, user_id=standard_user.id, path="/y")
        assert pv_service.count_visits(db, user_id=standard_user.id) == 1


class TestGetPopularPages:
    def test_returns_popular(self, db, admin_user):
        for _ in range(3):
            pv_service.record_visit(db, user_id=admin_user.id, path="/dashboard")
        pv_service.record_visit(db, user_id=admin_user.id, path="/vehicles")
        popular = pv_service.get_popular_pages(db)
        assert len(popular) == 2
        assert popular[0][0] == "/dashboard"
        assert popular[0][1] == 3


class TestGetActiveUsers:
    def test_returns_standard_users_only(self, db, admin_user, standard_user):
        pv_service.record_visit(db, user_id=admin_user.id, path="/admin")
        pv_service.record_visit(db, user_id=standard_user.id, path="/dash")
        active = pv_service.get_active_users(db)
        assert len(active) == 1
        assert active[0][1] == standard_user.username


class TestGetDailyVisits:
    @pytest.mark.skip(reason="cast(Date) not supported on SQLite test backend")
    def test_returns_daily_data(self, db, admin_user):
        pv_service.record_visit(db, user_id=admin_user.id, path="/x")
        daily = pv_service.get_daily_visits(db, days=7)
        assert len(daily) >= 1
        total = sum(d[1] for d in daily)
        assert total >= 1


class TestGetHourlyDistribution:
    def test_returns_24_hours(self, db, admin_user):
        pv_service.record_visit(db, user_id=admin_user.id, path="/x")
        hourly = pv_service.get_hourly_distribution(db, days=1)
        assert len(hourly) == 24
        total = sum(h[1] for h in hourly)
        assert total >= 1
