from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

TARGET_COLUMN = "Late_delivery_risk"
ORDER_ID_COLUMN = "Order Id"
ITEM_ID_COLUMN = "Order Item Id"
ORDER_DATE_COLUMN = "order date (DateOrders)"
ORDER_CATEGORICAL_COLUMNS = [
    "Shipping Mode",
    "Customer Segment",
    "Market",
    "Order Region",
]
NUMERIC_ITEM_COLUMNS = {
    "Product Category Id": "category",
    "Order Item Product Price": "price",
    "Order Item Quantity": "quantity",
    "Order Item Discount": "discount",
}
REQUIRED_COLUMNS = [
    ORDER_ID_COLUMN,
    ITEM_ID_COLUMN,
    TARGET_COLUMN,
    ORDER_DATE_COLUMN,
    *ORDER_CATEGORICAL_COLUMNS,
    *NUMERIC_ITEM_COLUMNS,
]
DEFAULT_INPUT = Path("data/raw/DataCoSupplyChainDataset.csv")
DEFAULT_OUTPUT = Path("data/cleaned/orders.parquet")


def build_order_features(source: pd.DataFrame) -> pd.DataFrame:
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(source.columns))
    if missing_columns:
        raise ValueError(f"Faltan columnas obligatorias en DataCo: {missing_columns}")

    data = source[REQUIRED_COLUMNS].copy()
    for column in [ORDER_ID_COLUMN, ITEM_ID_COLUMN, *ORDER_CATEGORICAL_COLUMNS]:
        data[column] = data[column].astype("string").str.strip()

    numeric_columns = [TARGET_COLUMN, *NUMERIC_ITEM_COLUMNS]
    for column in numeric_columns:
        original = data[column]
        converted = pd.to_numeric(original, errors="coerce")
        invalid = converted.isna() | ~np.isfinite(converted)
        if invalid.any():
            raise ValueError(f"Valores numéricos vacíos o inválidos en {column}")
        data[column] = converted

    if data[[ORDER_ID_COLUMN, ITEM_ID_COLUMN, *ORDER_CATEGORICAL_COLUMNS]].isna().any().any():
        raise ValueError("Hay identificadores o atributos de pedido vacíos")
    if data[[ORDER_ID_COLUMN, ITEM_ID_COLUMN, *ORDER_CATEGORICAL_COLUMNS]].eq("").any().any():
        raise ValueError("Hay identificadores o atributos de pedido vacíos")
    if data[ITEM_ID_COLUMN].duplicated().any():
        raise ValueError("Order Item Id debe ser único; hay líneas duplicadas")
    if not data[TARGET_COLUMN].isin([0, 1]).all():
        raise ValueError("Late_delivery_risk debe contener únicamente 0 o 1")

    integer_columns = ["Product Category Id", "Order Item Quantity"]
    for column in integer_columns:
        if not data[column].mod(1).eq(0).all():
            raise ValueError(f"{column} debe contener valores enteros")
        data[column] = data[column].astype("int64")
    if (data["Order Item Product Price"] <= 0).any():
        raise ValueError("Order Item Product Price debe ser mayor que cero")
    if (data["Order Item Quantity"] <= 0).any():
        raise ValueError("Order Item Quantity debe ser mayor que cero")
    if (data["Order Item Discount"] < 0).any():
        raise ValueError("Order Item Discount no puede ser negativo")

    data[ORDER_DATE_COLUMN] = pd.to_datetime(data[ORDER_DATE_COLUMN], errors="coerce")
    if data[ORDER_DATE_COLUMN].isna().any():
        raise ValueError("Hay fechas de pedido vacías o inválidas")

    consistent_columns = [
        TARGET_COLUMN,
        ORDER_DATE_COLUMN,
        *ORDER_CATEGORICAL_COLUMNS,
    ]
    inconsistent = (
        data.groupby(ORDER_ID_COLUMN, sort=False)[consistent_columns]
        .nunique(dropna=False)
        .gt(1)
        .any(axis=1)
    )
    if inconsistent.any():
        raise ValueError(
            f"Etiqueta o atributos inconsistentes en {int(inconsistent.sum())} pedidos"
        )

    data["order_hour"] = data[ORDER_DATE_COLUMN].dt.hour
    data["order_day_of_week"] = data[ORDER_DATE_COLUMN].dt.dayofweek
    data["order_month"] = data[ORDER_DATE_COLUMN].dt.month
    data["line_value"] = data["Order Item Product Price"] * data["Order Item Quantity"]

    grouped = data.groupby(ORDER_ID_COLUMN, sort=True)
    orders = grouped.agg(
        order_hour=("order_hour", "first"),
        order_day_of_week=("order_day_of_week", "first"),
        order_month=("order_month", "first"),
        num_items=(ITEM_ID_COLUMN, "count"),
        total_quantity=("Order Item Quantity", "sum"),
        total_product_value=("line_value", "sum"),
        total_discount=("Order Item Discount", "sum"),
        mean_item_discount=("Order Item Discount", "mean"),
        unique_product_categories=("Product Category Id", "nunique"),
        **{column: (column, "first") for column in ORDER_CATEGORICAL_COLUMNS},
        **{TARGET_COLUMN: (TARGET_COLUMN, "first")},
    )

    category_counts = (
        data.groupby([ORDER_ID_COLUMN, "Product Category Id"], sort=True)
        .size()
        .unstack(fill_value=0)
    )
    category_counts.columns = [f"category_{int(category)}_items" for category in category_counts.columns]
    orders = orders.join(category_counts, how="left")
    orders = pd.get_dummies(
        orders,
        columns=ORDER_CATEGORICAL_COLUMNS,
        dtype="int8",
    )

    feature_columns = sorted(column for column in orders.columns if column != TARGET_COLUMN)
    orders = orders[feature_columns + [TARGET_COLUMN]].reset_index(drop=True)
    non_numeric = orders.select_dtypes(exclude="number").columns.tolist()
    if non_numeric:
        raise ValueError(f"El dataset limpio contiene columnas no numéricas: {non_numeric}")
    return orders


def clean_csv(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> pd.DataFrame:
    header = pd.read_csv(input_path, encoding="cp1252", nrows=0).columns
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(header))
    if missing_columns:
        raise ValueError(f"Faltan columnas obligatorias en DataCo: {missing_columns}")

    source = pd.read_csv(
        input_path,
        encoding="cp1252",
        usecols=REQUIRED_COLUMNS,
        low_memory=False,
    )
    orders = build_order_features(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    orders.to_parquet(output_path, index=False)
    return orders


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Limpia DataCo y genera features numéricas agregadas por pedido."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    orders = clean_csv(args.input, args.output)
    print(f"Pedidos limpios: {len(orders)} | columnas: {len(orders.columns)}")
    print(f"Salida: {args.output}")


if __name__ == "__main__":
    main()