import pandas as pd
import pytest

from src.data.clean import build_order_features, clean_csv


def sample_source() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Order Id": [10, 10, 11],
            "Order Item Id": [1, 2, 3],
            "Late_delivery_risk": [1, 1, 0],
            "order date (DateOrders)": [
                "01/02/2018 03:00",
                "01/02/2018 03:00",
                "02/02/2018 10:00",
            ],
            "Shipping Mode": ["Standard Class", "Standard Class", "First Class"],
            "Customer Segment": ["Consumer", "Consumer", "Corporate"],
            "Market": ["USCA", "USCA", "Europe"],
            "Order Region": ["West of USA", "West of USA", "Western Europe"],
            "Product Category Id": [3, 4, 3],
            "Order Item Product Price": [10.0, 5.0, 20.0],
            "Order Item Quantity": [2, 1, 1],
            "Order Item Discount": [1.0, 0.5, 0.0],
        }
    )


def test_build_order_features_aggregates_items_and_excludes_identifiers() -> None:
    cleaned = build_order_features(sample_source())

    assert len(cleaned) == 2
    first_order = cleaned.loc[cleaned["Late_delivery_risk"] == 1].iloc[0]
    assert first_order["num_items"] == 2
    assert first_order["total_quantity"] == 3
    assert first_order["total_product_value"] == 25.0
    assert first_order["total_discount"] == 1.5
    assert first_order["unique_product_categories"] == 2
    assert first_order["category_3_items"] == 1
    assert first_order["category_4_items"] == 1
    assert first_order["Shipping Mode_Standard Class"] == 1
    assert "Order Id" not in cleaned.columns
    assert "Order Item Id" not in cleaned.columns
    assert cleaned.select_dtypes(exclude="number").empty


def test_build_order_features_rejects_inconsistent_order_target() -> None:
    source = sample_source()
    source.loc[1, "Late_delivery_risk"] = 0

    with pytest.raises(ValueError, match="inconsistentes"):
        build_order_features(source)


def test_clean_csv_writes_parquet(tmp_path) -> None:
    source_path = tmp_path / "raw.csv"
    output_path = tmp_path / "cleaned" / "orders.parquet"
    sample_source().to_csv(source_path, index=False, encoding="cp1252")

    cleaned = clean_csv(source_path, output_path)

    assert output_path.exists()
    assert len(pd.read_parquet(output_path)) == len(cleaned) == 2