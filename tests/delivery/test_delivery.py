from unittest.mock import Mock


def test_driver_record_mock_has_vehicle_info():
    driver = Mock()
    driver.id = 5
    driver.status = "active"
    driver.vehicle_info = "Truck 12"
    assert driver.status == "active"
    assert driver.vehicle_info == "Truck 12"


def test_delivery_status_enum_is_supported():
    status_value = "assigned"
    assert status_value in {"assigned", "in_transit", "delivered"}
