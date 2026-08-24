from security.models import UndoLog


def test_undo_log_has_restore_method():
    log = UndoLog(item_type="order", item_id=1, item_name="Order #1")
    assert hasattr(log, "restore") is True


def test_restore_method_returns_false_for_unsupported_item_type():
    log = UndoLog(item_type="unknown", item_id=1, item_name="Unknown")
    result = log.restore()
    assert result == (False, "Unsupported item type for restore")


def test_restore_method_returns_false_when_already_restored():
    log = UndoLog(item_type="order", item_id=1, item_name="Order #1", is_restored=True)
    assert log.restore() == (False, "Already restored")
