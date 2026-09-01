"""
Khalti ePayment v2 service.

Docs: https://docs.khalti.com/khalti-epayment/
Endpoints:
  POST {BASE}/epayment/initiate/  -> pidx + payment_url
  POST {BASE}/epayment/lookup/    -> status verification

All amounts are in paisa (int). Never trust client-supplied amount.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.payment import Payment
from app.models.subscription import BillingCycle
from app.models.user import User

logger = logging.getLogger(__name__)


def _price_for_cycle(billing_cycle: BillingCycle) -> int:
    if billing_cycle == BillingCycle.MONTHLY:
        return settings.SUBSCRIPTION_PRICE_MONTHLY_PAISE
    if billing_cycle == BillingCycle.YEARLY:
        return settings.SUBSCRIPTION_PRICE_YEARLY_PAISE
    raise ValueError(f"Invalid billing_cycle for payment: {billing_cycle}")


def _headers() -> dict:
    if not settings.KHALTI_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Khalti is not configured. Set KHALTI_SECRET_KEY on the server.",
        )
    # Khalti expects exactly "key <secret>" (lowercase key historic).
    # Docs show "key ..." in initiate; lookup also accepts "Key ...".
    # We send "key" to match docs example.
    return {
        "Authorization": f"key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    return settings.KHALTI_BASE_URL.rstrip("/")


class KhaltiService:
    """Stateless service; payment rows are the audit log."""

    async def initiate_payment(
        self,
        db: AsyncSession,
        user: User,
        billing_cycle: BillingCycle,
    ) -> Tuple[Payment, dict]:
        """
        Create a Khalti payment attempt and persist the Payment row.

        Returns (payment_row, khalti_response_json).
        """
        if billing_cycle == BillingCycle.NONE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="billing_cycle must be MONTHLY or YEARLY",
            )

        amount = _price_for_cycle(billing_cycle)

        # Unique merchant order id — used for idempotency & lookup.
        purchase_order_id = f"mentora-{user.id}-{billing_cycle.value}-{uuid.uuid4().hex[:12]}"
        purchase_order_name = f"Mentora Pro — {billing_cycle.value.title()}"

        payload = {
            "return_url": settings.KHALTI_RETURN_URL,
            "website_url": settings.KHALTI_WEBSITE_URL,
            "amount": amount,
            "purchase_order_id": purchase_order_id,
            "purchase_order_name": purchase_order_name,
            "customer_info": {
                "name": user.full_name or user.username,
                "email": user.email,
                # Khalti wants a phone; use placeholder if not available.
                "phone": getattr(user, "phone", None) or "9800000001",
            },
        }

        url = f"{_base_url()}/epayment/initiate/"
        logger.info("Khalti initiate %s amount=%s url=%s", purchase_order_id, amount, url)

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=_headers(), json=payload)
            # Khalti returns 200 on success, 400 on validation error.
            if resp.status_code != 200:
                try:
                    err = resp.json()
                except Exception:
                    err = {"detail": resp.text}
                logger.warning("Khalti initiate failed %s %s", resp.status_code, err)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=err,
                )
            data = resp.json()

        pidx = data.get("pidx")
        payment_url = data.get("payment_url")
        expires_at_raw = data.get("expires_at")

        if not pidx or not payment_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid response from Khalti (missing pidx/payment_url)",
            )

        expires_at = None
        if expires_at_raw:
            try:
                # e.g. 2023-05-25T16:26:16.471649+05:45
                expires_at = datetime.fromisoformat(expires_at_raw)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            except Exception:
                expires_at = None

        payment = Payment(
            user_id=user.id,
            purchase_order_id=purchase_order_id,
            purchase_order_name=purchase_order_name,
            pidx=pidx,
            billing_cycle=billing_cycle.value,
            amount=amount,
            status=data.get("status", "INITIATED") or "INITIATED",
            payment_url=payment_url,
            expires_at=expires_at,
            raw_response=json.dumps(data),
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return payment, data

    async def lookup_payment(
        self,
        db: AsyncSession,
        user_id: int,
        pidx: str,
    ) -> Tuple[Payment, dict]:
        """
        Call Khalti lookup for a pidx, update local Payment row, and return (payment, khalti_data).

        Ownership check: pidx must belong to user_id or raise 404.
        """
        # Ensure we own this pidx.
        result = await db.execute(select(Payment).where(Payment.pidx == pidx))
        payment: Optional[Payment] = result.scalars().first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found for this pidx",
            )
        if payment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this payment",
            )

        url = f"{_base_url()}/epayment/lookup/"
        logger.info("Khalti lookup pidx=%s user=%s", pidx, user_id)

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=_headers(), json={"pidx": pidx})
            if resp.status_code not in (200, 400):
                try:
                    err = resp.json()
                except Exception:
                    err = {"detail": resp.text}
                logger.warning("Khalti lookup failed %s %s", resp.status_code, err)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=err,
                )
            data = resp.json()

        # Khalti may return 400 for Expired/User canceled but still with JSON status.
        # Update local row with whatever status Khalti reports.
        khalti_status = data.get("status") or payment.status
        payment.status = khalti_status
        payment.transaction_id = data.get("transaction_id") or payment.transaction_id
        payment.tidx = data.get("transaction_id") or payment.tidx
        payment.total_amount = data.get("total_amount") or payment.total_amount
        fee = data.get("fee")
        if fee is not None:
            try:
                payment.fee = int(fee)
            except Exception:
                pass
        # Update raw audit.
        try:
            existing = json.loads(payment.raw_response) if payment.raw_response else {}
        except Exception:
            existing = {}
        existing["lookup"] = data
        payment.raw_response = json.dumps(existing)

        # Amount tamper check: Khalti total_amount must match our amount for Completed.
        if khalti_status == "Completed":
            khalti_amount = data.get("total_amount")
            if khalti_amount is not None and int(khalti_amount) != payment.amount:
                logger.error(
                    "Khalti amount mismatch pidx=%s expected=%s got=%s",
                    pidx,
                    payment.amount,
                    khalti_amount,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Amount mismatch: expected {payment.amount} got {khalti_amount}",
                )

        await db.commit()
        await db.refresh(payment)
        return payment, data

    async def list_user_payments(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 20,
    ):
        result = await db.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()


khalti_service = KhaltiService()
