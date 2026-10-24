import pandas as pd
import pytest

from src.data.clean import (
    TARGET_COLUMN,
    build_order_features,
    build_shipment_features,
    clean_csv,
)


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
    assert first_order["order_timestamp"] == (
        pd.Timestamp("2018-01-02 03:00").value // 10**9
    )
    assert first_order["category_3_items"] == 1
    assert first_order["category_4_items"] == 1
    assert first_order["Shipping Mode_Standard Class"] == 1
    assert "Order Id" not in cleaned.columns
    assert "Order Item Id" not in cleaned.columns
    assert cleaned.select_dtypes(exclude="number").empty


def test_build_shipment_features_matches_training_features() -> None:
    cleaned = build_order_features(sample_source())
    feature_names = [column for column in cleaned.columns if column != TARGET_COLUMN]
    shipment = {
        "order_date": "2018-01-02T03:00:00",
        "shipping_mode": "Standard Class",
        "customer_segment": "Consumer",
        "market": "USCA",
        "order_region": "West of USA",
        "order_items": [
            {
                "product_category_id": 3,
                "product_price": 10.0,
                "order_item_quantity": 2,
                "order_item_discount": 1.0,
            },
            {
                "product_category_id": 4,
                "product_price": 5.0,
                "order_item_quantity": 1,
                "order_item_discount": 0.5,
            },
        ],
    }

    transformed = build_shipment_features(shipment, feature_names)
    expected = cleaned.loc[cleaned[TARGET_COLUMN] == 1, feature_names].reset_index(drop=True)

    pd.testing.assert_frame_equal(transformed, expected)


def test_build_shipment_features_uses_training_columns_for_unseen_categories() -> None:
    feature_names = [
        "order_timestamp",
        "order_hour",
        "order_day_of_week",
        "order_month",
        "num_items",
        "total_quantity",
        "total_product_value",
        "total_discount",
        "mean_item_discount",
        "unique_product_categories",
        "Shipping Mode_First Class",
        "Shipping Mode_Standard Class",
        "category_3_items",
    ]
    shipment = {
        "order_date": "2018-01-02T03:00:00",
        "shipping_mode": "Unknown Mode",
        "customer_segment": "Unknown Segment",
        "market": "Unknown Market",
        "order_region": "Unknown Region",
        "order_items": [
            {
                "product_category_id": 99,
                "product_price": 10.0,
                "order_item_quantity": 1,
                "order_item_discount": 0.0,
            }
        ],
    }

    transformed = build_shipment_features(shipment, feature_names)

    assert transformed.columns.tolist() == feature_names
    assert transformed.loc[0, "Shipping Mode_First Class"] == 0
    assert transformed.loc[0, "Shipping Mode_Standard Class"] == 0
    assert transformed.loc[0, "category_3_items"] == 0


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