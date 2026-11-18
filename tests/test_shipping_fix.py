import inspect
import src.shipping as shipping


def test_credentials_not_hardcoded():
    source = inspect.getsource(shipping)
    assert "a9cdf3b2" not in source, "NP_API_KEY still hardcoded!"
    assert "company_shipper_2019" not in source, "UP_LOGIN still hardcoded!"
    assert "UkrPoshta#2019" not in source, "UP_PASSWORD still hardcoded!"
    assert "internal_courier_prod" not in source, "COURIER_TOKEN still hardcoded!"
