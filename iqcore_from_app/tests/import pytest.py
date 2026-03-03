import pytest
from core.onboarding import onboard_merchant

def test_onboard_merchant_success():
    merchant_info = {"name": "Test Store", "email": "test@store.com"}
    result = onboard_merchant(merchant_info)
    assert result["status"] == "success"

def test_onboard_merchant_missing_email():
    merchant_info = {"name": "Test Store"}
    with pytest.raises(ValueError):
        onboard_merchant(merchant_info)