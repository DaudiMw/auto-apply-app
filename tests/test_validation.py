from utils.validation import validate_address


def test_validate_address_valid():
    valid = {
        "street": "123 Main St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "country": "USA",
    }
    assert validate_address(valid) is True

    valid_plus_4 = {
        "street": "123 Main St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701-1234",
    }
    assert validate_address(valid_plus_4) is True


def test_validate_address_invalid():
    # Empty
    assert validate_address({}) is False

    # Missing zip
    missing_zip = {
        "street": "123 Main St",
        "city": "Austin",
        "state": "TX",
    }
    assert validate_address(missing_zip) is False

    # Invalid zip format
    invalid_zip = {
        "street": "123 Main St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "7870A",
    }
    assert validate_address(invalid_zip) is False
