"""
Billing API Endpoints
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid
from decimal import Decimal

from app.schemas.billing import (
    CreditPurchaseRequest, CreditPurchaseResponse,
    InvoiceResponse, PaymentRequest, PaymentResponse,
    BillingHistoryResponse, CostEstimateResponse,
    CreditBalanceResponse
)
from app.services.billing_service import BillingService
from app.database.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user's credit balance and billing information
    """
    try:
        billing_service = BillingService(db)
        balance_info = await billing_service.get_user_credits(current_user.id)
        
        if "error" in balance_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=balance_info["error"]
            )
        
        return balance_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get credit balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get credit balance"
        )

@router.post("/purchase-credits", response_model=CreditPurchaseResponse)
async def purchase_credits(
    purchase_data: CreditPurchaseRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Purchase credits for user account
    """
    try:
        billing_service = BillingService(db)
        
        # Add credits (in real implementation, this would process payment first)
        result = await billing_service.add_credits(
            user_id=current_user.id,
            credits_amount=purchase_data.credits_amount,
            transaction_type="purchase",
            payment_method=purchase_data.payment_method,
            payment_reference=purchase_data.payment_reference,
            metadata={
                "payment_gateway": purchase_data.payment_gateway,
                "currency": purchase_data.currency
            }
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        logger.info(f"Credits purchased: {purchase_data.credits_amount} for user {current_user.id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to purchase credits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to purchase credits"
        )

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    include_paid: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user's invoices
    """
    try:
        billing_service = BillingService(db)
        invoices = await billing_service.get_outstanding_invoices(
            user_id=current_user.id,
            include_paid=include_paid
        )
        
        return invoices
        
    except Exception as e:
        logger.error(f"Failed to get invoices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get invoices"
        )

@router.post("/invoices/generate")
async def generate_invoice(
    background_tasks: BackgroundTasks,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Generate deferred payment invoice
    """
    try:
        billing_service = BillingService(db)
        
        # Parse dates if provided
        from datetime import datetime
        start_date = None
        end_date = None
        
        if period_start:
            start_date = datetime.fromisoformat(period_start).date()
        if period_end:
            end_date = datetime.fromisoformat(period_end).date()
        
        result = await billing_service.generate_deferred_invoice(
            user_id=current_user.id,
            period_start=start_date,
            period_end=end_date
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        # Check for overdue invoices in background
        background_tasks.add_task(
            billing_service.check_overdue_invoices
        )
        
        logger.info(f"Invoice generated: {result['invoice_number']}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate invoice"
        )

@router.post("/invoices/{invoice_id}/pay", response_model=PaymentResponse)
async def pay_invoice(
    invoice_id: uuid.UUID,
    payment_data: PaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Process payment for invoice
    """
    try:
        billing_service = BillingService(db)
        
        # Verify invoice belongs to user
        from sqlalchemy import select
        stmt = select(DeferredPayment).where(
            and_(
                DeferredPayment.id == invoice_id,
                DeferredPayment.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        
        # Process payment
        payment_result = await billing_service.process_payment(
            invoice_id=invoice_id,
            payment_method=payment_data.payment_method,
            payment_reference=payment_data.payment_reference,
            amount=payment_data.amount,
            currency=payment_data.currency
        )
        
        if not payment_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=payment_result["error"]
            )
        
        logger.info(f"Invoice paid: {invoice_id}")
        
        return payment_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pay invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pay invoice"
        )

@router.get("/history", response_model=BillingHistoryResponse)
async def get_billing_history(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user's billing history
    """
    try:
        billing_service = BillingService(db)
        history = await billing_service.get_billing_history(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        return history
        
    except Exception as e:
        logger.error(f"Failed to get billing history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get billing history"
        )

@router.get("/cost-estimate", response_model=CostEstimateResponse)
async def get_cost_estimate(
    period_days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Estimate monthly cost based on usage
    """
    try:
        billing_service = BillingService(db)
        estimate = await billing_service.estimate_monthly_cost(
            user_id=current_user.id,
            based_on_period=period_days
        )
        
        if "error" in estimate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=estimate["error"]
            )
        
        return estimate
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cost estimate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cost estimate"
        )

@router.get("/pricing")
async def get_pricing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get service pricing information
    """
    try:
        billing_service = BillingService(db)
        
        pricing_info = {
            "credit_price": settings.CREDIT_PRICE,
            "currency": settings.DEFAULT_CURRENCY,
            "services": billing_service.pricing,
            "trial": {
                "days": settings.TRIAL_DAYS,
                "credits": settings.TRIAL_CREDITS
            },
            "deferred_payment": {
                "grace_days": settings.DEFERRED_PAYMENT_GRACE_DAYS,
                "min_amount": settings.MIN_DEFERRED_AMOUNT,
                "late_fee_percentage": settings.LATE_FEE_PERCENTAGE
            }
        }
        
        return pricing_info
        
    except Exception as e:
        logger.error(f"Failed to get pricing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pricing information"
        )

@router.post("/calculate-cost")
async def calculate_service_cost(
    service_type: str,
    quantity: int = 1,
    duration: Optional[int] = None,
    custom_rate: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Calculate cost for a specific service
    """
    try:
        billing_service = BillingService(db)
        
        cost = await billing_service.calculate_service_cost(
            service_type=service_type,
            quantity=quantity,
            duration=duration,
            custom_rate=Decimal(str(custom_rate)) if custom_rate else None
        )
        
        monetary_cost = float(cost * Decimal(str(settings.CREDIT_PRICE)))
        
        return {
            "service_type": service_type,
            "quantity": quantity,
            "duration": duration,
            "credits_required": float(cost),
            "monetary_cost": monetary_cost,
            "currency": settings.DEFAULT_CURRENCY,
            "credit_price": settings.CREDIT_PRICE
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate cost: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate service cost"
        )

@router.get("/usage/current-period")
async def get_current_period_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get usage for current billing period
    """
    try:
        billing_service = BillingService(db)
        
        # Get billing period
        from sqlalchemy import select
        stmt = select(User).where(User.id == current_user.id)
        result = await db.execute(stmt)
        user = result.scalar_one()
        
        period_start = billing_service._get_billing_period_start(user)
        
        usage = await billing_service._calculate_period_usage(
            user_id=current_user.id,
            period_start=period_start
        )
        
        return {
            "user_id": current_user.id,
            "period_start": period_start,
            "period_end": datetime.utcnow().date(),
            "usage": usage
        }
        
    except Exception as e:
        logger.error(f"Failed to get current period usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage information"
        )

@router.post("/notifications/test")
async def test_billing_notification(
    notification_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Test billing notification (admin only)
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        billing_service = BillingService(db)
        email_service = EmailService()
        
        # Test different notification types
        if notification_type == "invoice":
            await email_service.send_invoice_email(
                email=current_user.email,
                name=current_user.full_name or current_user.username,
                invoice_number="TEST-INV-001",
                amount=99.99,
                currency="USD",
                due_date=date.today() + timedelta(days=7),
                period_start=date.today() - timedelta(days=30),
                period_end=date.today()
            )
            
        elif notification_type == "payment":
            await email_service.send_payment_confirmation(
                email=current_user.email,
                name=current_user.full_name or current_user.username,
                invoice_number="TEST-INV-001",
                amount=99.99,
                currency="USD",
                payment_method="credit_card",
                payment_date=date.today()
            )
            
        elif notification_type == "overdue":
            await email_service.send_overdue_reminder(
                email=current_user.email,
                name=current_user.full_name or current_user.username,
                invoice_number="TEST-INV-001",
                amount=99.99,
                currency="USD",
                overdue_days=7,
                due_date=date.today() - timedelta(days=7)
            )
            
        elif notification_type == "credits":
            await email_service.send_credits_added_notification(
                email=current_user.email,
                name=current_user.full_name or current_user.username,
                credits_added=1000,
                total_credits=2000,
                amount_paid=10.00
            )
        
        return {
            "success": True,
            "message": f"Test notification sent: {notification_type}",
            "recipient": current_user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send test notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test notification"
        )