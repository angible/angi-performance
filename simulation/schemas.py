"""
Pydantic schemas for Self-Checkout (SCO) transaction and alert management.

This module defines request and response models for various transaction-related 
operations in a self-checkout system. The schemas are used to validate and 
structure data for different stages of a transaction, including:

- Transaction start and completion
- Item addition and removal
- System state changes
- Alert generation and reporting

Each model uses Pydantic's `Field` to provide detailed metadata, including:
- Example values
- Descriptions
- Default values
- Type hints

These schemas ensure data integrity, provide clear documentation, 
and enable automatic request/response validation in the API.

Key Models:
- TransactionStartRequestBody: Initiates a new transaction
- TransactionCompleteRequestBody: Finalizes a transaction
- ItemAddRequestBody: Adds an item to a transaction
- ItemRemoveRequestBody: Removes an item from a transaction
- StateRequestBody: Manages UI and system state changes
- AlertResponse: Represents system alerts and anomalies
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from enum import Enum, StrEnum


class TransactionStartRequestBody(BaseModel):
    transaction_id: str = Field(
        example="txn-123456",
        description="Unique identifier for the transaction",
    )
    transaction_type: str = Field(
        example="pending",
        description="Transaction type (e.g., `pending`, `paid`)",
    )
    timestamp: int = Field(
        example=1742355063000,
        description="Timestamp",
    )
    status: str = "started"
    server_timestamp: int = Field(
        default=0,
        example=1742355063000,
        description="Timestamp",
    )


class TransactionCompleteRequestBody(BaseModel):
    transaction_id: str = Field(
        example="txn-123456",
        description="Unique identifier for the transaction",
    )
    transaction_type: str = Field(
        example="pending",
        description="Transaction type (e.g., `pending`, `paid`)",
    )
    total_items: int = Field(
        example=10,
        default=0,
        description="Total number of items scanned",
    )
    status: str = Field(
        example="completed",
        description="Status of the transaction "
        "(e.g., `checkout_ready_to_pay`, `checkout_abandoned`)",
        default="completed",
    )
    timestamp: int = Field(
        example=1742355063000,
        description="Timestamp",
    )
    server_timestamp: int = Field(
        default=0,
        example=1742355063000,
        description="Timestamp",
    )

class TransactionStartResponseBody(TransactionStartRequestBody):
    pass

class TransactionCompleteResponseBody(TransactionCompleteRequestBody):
    pass

class ScanStartRequestBody(BaseModel):
    transaction_id: str = Field(
        example="txn-123456",
        description="Unique identifier for the transaction",
    )
    transaction_type: str = Field(
        example="pending",
        description="Transaction type (e.g., `pending`, `paid`)",
    )
    timestamp: int = Field(
        example=1742355063000,
        description="Timestamp",
    )
    server_timestamp: int = Field(
        default=0,
        example=1742355063000,
        description="Timestamp",
    )

class ScanCompletedRequestBody(BaseModel):
    transaction_id: str = Field(
        example="txn-123456",
        description="Unique identifier for the transaction",
    )
    transaction_type: str = Field(
        example="pending",
        description="Transaction type (e.g., `pending`, `paid`)",
    )
    total_items: int = Field(
        default=0,
        example=10,
        description="The number of items scanned",
    )
    timestamp: int = Field(
        example=1742355063000,
        description="Timestamp",
    )
    server_timestamp: int = Field(
        default=0,
        example=1742355063000,
        description="Timestamp",
    )

class ScanStartResponseBody(ScanStartRequestBody):
    pass

class ScanCompletedResponseBody(ScanCompletedRequestBody):
    pass

class ItemAddRequestBody(BaseModel):
    transaction_id: str = Field(
        example="txn-123456",
        description="Unique identifier for the transaction",
    )
    transaction_type: str = Field(
        example="pending",
        default="pending",
        description="Transaction type (e.g., `pending`, `paid`)",
    )
    item_id: str = Field(
        example="51432",
        default="51432",
        description="Unique identifier for the item",
    )
    barcode: str = Field(
        example="1234567890123",
        default="1234567890123",
        description="Barcode of the item",
    )
    name: str = Field(
        example="Apple",
        default="Apple",
        description="Name of the item",
    )
    quantity: int = Field(
        example=2,
        default=1,
        description="Quantity added",
    )
    added_method: str = Field(
        example="scanner",
        default="scanner",
        description="Method of adding the item "
        "(e.g., `scanner`, `manual_input`, `handy_scanner`, `order`)",
    )
    timestamp: int = Field(
        example=1742355063000,
        description="Timestamp",
    )
    server_timestamp: int = Field(
        default=0,
        example=1742355063000,
        description="Timestamp",
    )
    is_kitchen_item: bool = Field(
        default=False,
        example=False,
        description="The item is from kitchen or not",
    )
    price: float | None = Field(
        default=None,
        example=5.8,
        description="Price of the item",
    )
    currency: str | None = Field(
        default=None,
        example="USD",
        description="Currency of the item",
    )



class ItemAddResponseBody(ItemAddRequestBody):
    pass


class ItemRemoveRequestBody(BaseModel):
    transaction_id: str = Field(
        example="txn-123456",
        description="Unique identifier for the transaction",
    )
    transaction_type: str = Field(
        example="pending",
        description="Transaction type (e.g., `pending`, `paid`)",
        default="pending",
    )
    item_id: str = Field(
        example="51432",
        description="Unique identifier for the item",
        default="51432",   
    )
    barcode: str = Field(
        example="1234567890123",
        description="Barcode of the item",
        default="1234567890123",
        
    )
    name: str = Field(
        example="Apple",
        description="Name of the item",
        default="Apple",
    )
    quantity: int = Field(
        example=2,
        description="Quantity added",
        default=1,
    )
    removed_user: str = Field(
        example="staff",
        description="(e.g., `staff`, `user`)",
        default="staff",
    )
    timestamp: int = Field(
        example=1742355063000,
        description="Timestamp",
    )
    server_timestamp: int = Field(
        default=0,
        example=1742355063000,
        description="Timestamp",
    )
    is_kitchen_item: bool = Field(
        default=False,
        example=False,
        description="The item is from kitchen or not",
    )

class ItemRemoveResponseBody(ItemRemoveRequestBody):
    pass

class StateRequestBody(BaseModel):
    transaction_id: str = Field(
        example="txn-123456",
        description="Unique identifier for the transaction",
    )
    transaction_type: str = Field(
        example="pending",
        description="Transaction type (e.g., `pending`, `paid`)",
    )
    ui_state: str = Field(
        example="staff_mode_on",
        description="UI state change "
        "(e.g., `staff_mode_on`, `system_pause`, `system_resume`)",
        default="staff_mode_on",
    )
    timestamp: int = Field(
        example=1742355063000,
        description="Timestamp",
    )
    server_timestamp: int = Field(
        default=0,
        example=1742355063000,
        description="Timestamp",
    )
    reason: str = Field(
        default=None,
        example="Manual override by staff",
        description="Reason for the UI state change (e.g., `Manual override by staff`)",
    )

class StateResponseBody(StateRequestBody):
    pass

class AdditionalInfoField(BaseModel):
    camera_id: str = Field(
        default="cam1",
        example="camera001",
        description="Camera identifier, if applicable",
    )
    image_paths: list[str] = Field(
        default=["example.jpg"],
        example=[
            "https://example.com/alert_images/uuid-1234-1.jpg?token=123",
            "https://example.com/alert_images/uuid-1234-2.jpg?token=123",
            "https://example.com/alert_images/uuid-1234-3.jpg?token=123",
        ],
        description="URL to an alert snapshot/image (if available)",
    )
    video_path: str | None = Field(
        default="example.mp4",
        example="https://example.com/alert_videos/uuid-1234-5678-9012.mp4?token=123",
        description="Path to an alert video (if available)",
    )
    ai_model_version: str = Field(
        default="1.0.0",
        example="1.0.0",
        description="model version"
    )
    ai_logic_version: str = Field(
        default="1.0.0",
        example="1.0.0",
        description="logic version"
    )


class AlertResponse(BaseModel):
    alert_id: str = Field(
        default="",
        example="uuid-1234-5678-9012",
        description="Unique identifier for the alert",
    )
    alert_type: str = Field(
        example="no-scan",
        description="Type of alert (e.g., `no-scan`, `items-count-not-matched`)",
    )
    store_id: str = Field(
        default="store123",
        example="store123",
        description="Unique store identifier",
    )
    store_name: str = Field(
        default="Wesgate",
        example="Downtown Supermarket",
        description="Store name for display",
    )
    sco_id: str = Field(
        example="SCO001",
        description="Unique identifier for the SCO device",
    )
    sco_name: str = Field(
        default="SelfCheckout-01",
        example="SelfCheckout-01",
        description="SCO device name for reference",
    )
    transaction_id: str = Field(
        example="txn-123456",
        description="Unique identifier for the transaction",
    )
    transaction_type: str = Field(
        example="pending",
        description="Transaction type (e.g., `pending`, `paid`)",
    )
    description: str = Field(
        example="Item detected but not scanned",
        description="Human-readable explanation of the alert",
    )
    severity: str = Field(
        example="high",
        description="`low`, `medium`, `high` (to help prioritize responses)",
    )
    additional_info: AdditionalInfoField | None = None
    timestamp: int | float = Field(
        example=1742355063000,
        description="Timestamp",
    )
    track_start_timestamp: int | float = Field(
        example=1742355063000,
        description="Start timestamp of the alert",
    )
    track_end_timestamp: int | float = Field(
        example=1742355064000,
        description="End timestamp of the alert",
    )
    track_id: int | None = Field(
        default=None,
        example=123,
        description="Tracker ID associated with the alert (if applicable)",
    )
    video_path_from_image_cache: str | None = Field(
        default=None,
        example="https://example.com/alert_videos/uuid-1234-5678-9012.mp4?token=123",
        description="Path to an alert video (if available)",
    )
    frame_index: int | None = Field(
        default=None,
        example=123,
        description="Frame index associated with the alert (if applicable)",
    )
    track_start_frame_index: int | None = Field(
        default=None,
        example=123,
        description="Frame index associated with the alert (if applicable)",
    )
    track_end_frame_index: int | None = Field(
        default=None,
        example=123,
        description="Frame index associated with the alert (if applicable)",
    )

class WeightingScaleNotMatchedRequestBody(BaseModel):
    transaction_id: str = Field(
        example="txn-123456",
        description="Unique identifier for the transaction",
    )
    transaction_type: str = Field(
        example="pending",
        description="Transaction type (e.g., `pending`, `paid`)",
    )
    item_id: str = Field(
        example="51432",
        description="Unique identifier for the item",
        default="aabb513",
    )
    name: str = Field(
        example="Apple",
        description="Name of the item",
        default="aabbabc",
    )
    barcode: str = Field(
        example="1234567890123",
        description="Barcode of the item",
    )
    detected_weight: float = Field(
        example=50.0,
        description="Detected weight of the item",
        default=50.0,
    )
    expected_weight: float = Field(
        example=100.0,
        description="Expected weight of the item",
        default=100.0,
    )
    timestamp: int = Field(
        example=1742355063000,
        description="Timestamp",
    )
    server_timestamp: int = Field(
        default=0,
        example=1742355063000,
        description="Timestamp",
    )


class WeightingScaleNotMatchedResponseBody(WeightingScaleNotMatchedRequestBody):
    pass

class MediaMjpegFeedQueryParams(BaseModel):
    fps: int = 10
    height: int = 480
    bbox: Optional[int] = None
    timestamp: Optional[int] = None
    zones: Optional[int] = None
    mask: Optional[int] = None
    motion: Optional[int] = None
    regions: Optional[int] = None

class Extension(str, Enum):
    webp = "webp"
    png = "png"
    jpg = "jpg"
    jpeg = "jpeg"

class MediaLatestFrameQueryParams(BaseModel):
    bbox: Optional[int] = None
    timestamp: Optional[int] = None
    zones: Optional[int] = None
    mask: Optional[int] = None
    motion: Optional[int] = None
    regions: Optional[int] = None
    quality: Optional[int] = 70
    height: Optional[int] = None
    store: Optional[int] = None

class BarcodeTypeId(Enum):
    WEIGHTING_SCALE_NOT_MATCHED = 0
    STATE = 1
    ITEM_REMOVED = 2
    ITEM_ADDED = 3
    TRANSACTION_COMPLETED = 4
    TRANSACTION_STARTED = 5
    SCAN_STARTED = 6
    SCAN_COMPLETED = 7

    @classmethod
    def get_id_by_name(cls, name):
        for id_name in cls:
            if id_name.name == name:
                return id_name.value
        return None

    @classmethod
    def get_name_by_id(cls, id):
        for id_name in cls:
            if id_name.value == id:
                return id_name
        return None

class BarcodeType(StrEnum):
    WEIGHTING_SCALE_NOT_MATCHED = "weighting-scale-not-matched"
    STATE = "state"
    ITEM_REMOVED = "item-removed"
    ITEM_ADDED = "item-added"
    TRANSACTION_COMPLETED = "transaction-completed"
    TRANSACTION_STARTED = "transaction-started"
    SCAN_STARTED = "scan-started"
    SCAN_COMPLETED = "scan-completed"

    @classmethod
    def to_id_dict(cls):
        return {v:i for i, v in enumerate(cls)}

    @classmethod
    def get_by_name(cls, name):
        for c in cls:
            if c.name == name.name:
                return c
        return None

class BarcodeInfo(BaseModel):
    id: str = ""
    transaction_id: str = ""
    string: str
    scan_timestamp: float
    scan_frame_index: int
    receive_timestamp: float
    receive_frame_index: int
    processed: bool = False
    matched_id: int = -1
    has_used_medal: bool = False
    barcode_type: BarcodeType = BarcodeType.ITEM_ADDED
    barcode_type_id: int | None = None
    additional_info: (
        TransactionStartRequestBody
        | TransactionCompleteRequestBody
        | WeightingScaleNotMatchedRequestBody
        | ItemAddRequestBody
        | ItemRemoveRequestBody
        | StateRequestBody
        | ScanStartRequestBody
        | ScanCompletedRequestBody
        | None
    ) = None
    sco_id: str = ""
    transaction_type: str = "pending"
    server_timestamp: float = 0
    time_shift: float | None = None
    product_code: str | None = None

    def use_medal(self):
        self.has_used_medal = True

    def has_matched_behavior(self, matched_id=None):
        if matched_id is not None:
            return self.matched_id == matched_id
        return self.matched_id >= 0

    def model_post_init(self, __context):
        if self.barcode_type_id is None:
            self.barcode_type_id = BarcodeTypeId.get_id_by_name(self.barcode_type.name)
        if not self.transaction_id:
            self.transaction_id = self.id

    @field_validator('id', mode='before')
    @classmethod
    def convert_timestamp_to_int(cls, v):
        if v is None:
            return v
        # Convert float to int (timestamps are already in milliseconds)
        return str(v)

    class Config:
        user_enum_values = True  # barcode_type=<BarcodeType.ITEM_ADDED: 'item-added'> -> barcode_type='item-added'
