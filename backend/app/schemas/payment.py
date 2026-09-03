"""
Khalti payment schemas.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.subscription import BillingCycle


class KhaltiInitiateRequest(BaseModel):
    billing_cycle: BillingCycle


class KhaltiInitiateResponse(BaseModel):
    pidx: str
    payment_url: str
    expires_at: Optional[datetime] = None
    expires_in: Optional[int] = None
    purchase_order_id: str
    purchase_order_name: str
    amount: int  # paisa
    billing_cycle: BillingCycle


class KhaltiVerifyRequest(BaseModel):
    pidx: str


class KhaltiVerifyResponse(BaseModel):
    pidx: str
    status: str
    transaction_id: Optional[str] = None
    total_amount: Optional[int] = None
    fee: Optional[int] = None
    refunded: Optional[bool] = None
    purchase_order_id: str
    billing_cycle: str
    # If Completed, the activated subscription snapshot.
    subscription: Optional[dict] = None
    message: str


class PaymentOut(BaseModel):
    id: int
    purchase_order_id: str
    pidx: str
    billing_cycle: str
    amount: int
    total_amount: Optional[int] = None
    status: str
    payment_url: Optional[str] = None
    transaction_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
