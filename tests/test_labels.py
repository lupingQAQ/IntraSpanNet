from quietspan.labels import PRODUCTS, PRODUCT_TO_TIER, PRODUCT_TO_TYPE, describe


def test_product_table_is_complete():
    assert len(PRODUCTS) == 18
    assert len(set(PRODUCTS)) == 18
    assert set(PRODUCTS) == set(PRODUCT_TO_TIER) == set(PRODUCT_TO_TYPE)


def test_describe_returns_known_fields():
    row = describe("wazuh_agent")
    assert row["product"] == "wazuh_agent"
    assert row["tier"] == "安全软件"
    assert row["type"] == "EDR / HIDS"
    assert row["display"] == "Wazuh agent"


def test_describe_rejects_unknown():
    try:
        describe("not_a_product")
    except KeyError:
        return
    raise AssertionError("expected KeyError")
