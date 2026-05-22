"""Tests for app.services.audit service."""

from app.services import audit as audit_service


class TestLogAction:
    def test_creates_entry(self, db, admin_user):
        entry = audit_service.log_action(
            db,
            user_id=admin_user.id,
            action="create",
            target_type="vehicle",
            target_id=1,
            target_label="AB12 CDE",
            details="Created vehicle AB12 CDE",
        )
        assert entry.id is not None
        assert entry.action == "create"
        assert entry.target_type == "vehicle"
        assert entry.target_label == "AB12 CDE"

    def test_creates_entry_minimal(self, db, admin_user):
        entry = audit_service.log_action(
            db,
            user_id=admin_user.id,
            action="delete",
            target_type="location",
        )
        assert entry.id is not None
        assert entry.target_id is None
        assert entry.details is None


class TestGetAuditLogs:
    def test_returns_entries(self, db, admin_user):
        audit_service.log_action(db, user_id=admin_user.id, action="first", target_type="test")
        audit_service.log_action(db, user_id=admin_user.id, action="second", target_type="test")
        logs = audit_service.get_audit_logs(db)
        assert len(logs) == 2
        actions = {log.action for log in logs}
        assert actions == {"first", "second"}

    def test_respects_limit_and_offset(self, db, admin_user):
        for i in range(5):
            audit_service.log_action(db, user_id=admin_user.id, action=f"act_{i}", target_type="test")
        page = audit_service.get_audit_logs(db, limit=2, offset=0)
        assert len(page) == 2
        page2 = audit_service.get_audit_logs(db, limit=2, offset=2)
        assert len(page2) == 2


class TestCountAuditLogs:
    def test_returns_count(self, db, admin_user):
        for _ in range(3):
            audit_service.log_action(db, user_id=admin_user.id, action="test", target_type="test")
        assert audit_service.count_audit_logs(db) == 3
