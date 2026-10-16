from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class OrderItemFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_category_id: int = Field(
        gt=0,
        description="DataCo source: Product Category Id.",
    )
    product_price: float = Field(
        gt=0,
        allow_inf_nan=False,
        description="DataCo source: Order Item Product Price.",
    )
    order_item_quantity: int = Field(
        gt=0,
        description="DataCo source: Order Item Quantity.",
    )
    order_item_discount: float = Field(
        ge=0,
        allow_inf_nan=False,
        description="DataCo source: Order Item Discount.",
    )


class ShipmentFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_date: datetime = Field(
        description="Order creation time in ISO 8601 format; DataCo source: order date (DateOrders).",
    )
    shipping_mode: NonEmptyString = Field(
        description="DataCo source: Shipping Mode.",
    )
    customer_segment: NonEmptyString = Field(
        description="DataCo source: Customer Segment.",
    )
    market: NonEmptyString = Field(
        description="DataCo source: Market.",
    )
    order_region: NonEmptyString = Field(
        description="DataCo source: Order Region.",
    )
    order_items: list[OrderItemFeatures] = Field(
        min_length=1,
        description="Line items belonging to this order; DataCo has one row per order item.",
    )


class IngestResponse(BaseModel):
    status: str
    shipment: ShipmentFeatures


class HealthResponse(BaseModel):
    status: str


class PredictionResponse(BaseModel):
    delay_risk: bool
    delay_probability: float = Field(ge=0, le=1)
