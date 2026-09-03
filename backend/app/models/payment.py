"""
Payment model for Khalti ePayment integration.

Each row tracks a single Khalti pidx lifecycle: initiate -> redirect ->
lookup/verify -> subscription activation.

Uses paisa for amount to avoid float rounding.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, Text
from sqlalchemy.sql import func

from app.database.base import BaseModel


class PaymentStatus(str):
    INITIATED = "INITIATED"
    PENDING = "Pending"
    COMPLETED = "Completed"
    USER_CANCELED = "User canceled"
    EXPIRED = "Expired"
    REFUNDED = "Refunded"
    FAILED = "FAILED"


class Payment(BaseModel):
    """
    Khalti payment transaction.

    - purchase_order_id is merchant-generated and unique (prevents replay).
    - pidx is returned by Khalti and unique per attempt.
    - status mirrors Khalti lookup status; COMPLETED triggers subscription activation.
    """

    __tablename__ = "payments"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Merchant order id, e.g. mentora-12-MONTHLY-uuid
    purchase_order_id = Column(String(100), unique=True, nullable=False, index=True)
    purchase_order_name = Column(String(255), nullable=False, default="Mentora Pro Subscription")

    # Khalti identifiers
    pidx = Column(String(255), unique=True, nullable=False, index=True)
    transaction_id = Column(String(255), nullable=True)
    tidx = Column(String(255), nullable=True)

    billing_cycle = Column(String(20), nullable=False)  # MONTHLY | YEARLY
    amount = Column(Integer, nullable=False)  # paisa
    total_amount = Column(Integer, nullable=True)  # echoed from Khalti
    fee = Column(Integer, nullable=True, default=0)
    status = Column(String(50), nullable=False, default=PaymentStatus.INITIATED)
    refunded = Column(String(10), nullable=True)

    payment_url = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Raw JSON from Khalti for audit, stored as text.
    raw_response = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_payments_user_status", "user_id", "status"),
        Index("ix_payments_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Payment id={self.id} user_id={self.user_id} pidx={self.pidx} "
            f"cycle={self.billing_cycle} amount={self.amount} status={self.status}>"
        )
