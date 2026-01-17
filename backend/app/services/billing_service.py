"""
Billing Service for MATRXe - Deferred Payment System
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import json

from app.models.user import User
from app.models.billing import CreditTransaction, DeferredPayment
from app.models.digital_twin import DigitalTwin
from app.models.scheduled_tasks import ScheduledTask
from app.core.config import settings
from app.services.email_service import EmailService
from app.utils.currency import convert_currency

logger = logging.getLogger(__name__)

class BillingService:
    """
    Service handling billing, credits, and deferred payments
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()
        
        # Pricing configuration (in credits)
        self.pricing = {
            "voice_processing": {
                "per_minute": settings.VOICE_MINUTE_COST,
                "per_character": 1,
                "training": 100
            },
            "chat_processing": {
                "per_message": settings.CHAT_MESSAGE_COST,
                "per_token": 0.1
            },
            "face_processing": {
                "per_image": settings.FACE_PROCESSING_COST,
                "training": 200,
                "animation": 50
            },
            "storage": {
                "per_gb_per_month": 100,
                "per_file": 1
            },
            "tasks": {
                "per_task_execution": 5,
                "per_scheduled_task": 10
            }
        }
    
    async def get_user_credits(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user's credit balance and usage"""
        try:
            # Get user
            user = await self.db.get(User, user_id)
            if not user:
                return {"error": "User not found"}
            
            # Calculate usage for current billing period
            period_start = self._get_billing_period_start(user)
            usage = await self._calculate_period_usage(user_id, period_start)
            
            # Calculate deferred balance
            deferred_balance = await self._calculate_deferred_balance(user_id)
            
            return {
                "user_id": user_id,
                "total_credits": user.total_credits,
                "used_credits": user.used_credits,
                "available_credits": user.total_credits - user.used_credits,
                "deferred_balance": deferred_balance,
                "trial_end_date": user.trial_end_date,
                "is_trial_active": self._is_trial_active(user),
                "current_period_usage": usage,
                "credit_price": settings.CREDIT_PRICE,
                "currency": settings.DEFAULT_CURRENCY
            }
            
        except Exception as e:
            logger.error(f"Failed to get user credits: {e}")
            return {"error": str(e)}
    
    async def deduct_credits(
        self, 
        user_id: uuid.UUID, 
        service_type: str, 
        amount: Decimal,
        description: str,
        resource_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Deduct credits for service usage"""
        try:
            # Get user
            user = await self.db.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if user has enough credits
            available_credits = user.total_credits - user.used_credits
            if available_credits < amount:
                # Check if user is in trial and has trial credits
                if self._is_trial_active(user) and user.used_credits < settings.TRIAL_CREDITS:
                    # Still have trial credits
                    pass
                else:
                    return {
                        "success": False, 
                        "error": "Insufficient credits",
                        "available": available_credits,
                        "required": amount
                    }
            
            # Create transaction
            transaction = CreditTransaction(
                id=uuid.uuid4(),
                user_id=user_id,
                transaction_type="usage",
                amount=-float(amount),
                credits_used=int(amount),
                service_type=service_type,
                resource_id=resource_id,
                unit_price=float(settings.CREDIT_PRICE),
                total_price=float(amount * Decimal(str(settings.CREDIT_PRICE))),
                status="completed",
                metadata=metadata or {},
                description=description
            )
            
            # Update user credits
            user.used_credits += int(amount)
            user.total_spent += float(amount * Decimal(str(settings.CREDIT_PRICE)))
            
            # If in deferred payment mode, add to deferred balance
            if not self._is_trial_active(user) and user.subscription_tier == "trial":
                user.deferred_payment_balance += float(amount * Decimal(str(settings.CREDIT_PRICE)))
            
            self.db.add(transaction)
            await self.db.commit()
            
            logger.info(f"Deducted {amount} credits from user {user_id} for {service_type}")
            
            return {
                "success": True,
                "transaction_id": transaction.id,
                "credits_deducted": amount,
                "remaining_credits": user.total_credits - user.used_credits,
                "deferred_balance": user.deferred_payment_balance
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to deduct credits: {e}")
            return {"success": False, "error": str(e)}
    
    async def add_credits(
        self,
        user_id: uuid.UUID,
        credits_amount: int,
        transaction_type: str = "purchase",
        payment_method: Optional[str] = None,
        payment_reference: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Add credits to user account"""
        try:
            user = await self.db.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Calculate monetary value
            amount = credits_amount * settings.CREDIT_PRICE
            
            # Create transaction
            transaction = CreditTransaction(
                id=uuid.uuid4(),
                user_id=user_id,
                transaction_type=transaction_type,
                amount=float(amount),
                credits_granted=credits_amount,
                payment_method=payment_method,
                payment_reference=payment_reference,
                unit_price=float(settings.CREDIT_PRICE),
                total_price=float(amount),
                status="completed",
                metadata=metadata or {},
                description=f"Added {credits_amount} credits"
            )
            
            # Update user
            user.total_credits += credits_amount
            
            self.db.add(transaction)
            await self.db.commit()
            
            logger.info(f"Added {credits_amount} credits to user {user_id}")
            
            # Send notification
            await self.email_service.send_credits_added_notification(
                email=user.email,
                name=user.full_name or user.username,
                credits_added=credits_amount,
                total_credits=user.total_credits,
                amount_paid=amount
            )
            
            return {
                "success": True,
                "transaction_id": transaction.id,
                "credits_added": credits_amount,
                "total_credits": user.total_credits,
                "amount_paid": amount
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to add credits: {e}")
            return {"success": False, "error": str(e)}
    
    async def calculate_service_cost(
        self,
        service_type: str,
        quantity: int = 1,
        duration: Optional[int] = None,
        custom_rate: Optional[Decimal] = None
    ) -> Decimal:
        """Calculate cost for a service"""
        try:
            if custom_rate is not None:
                return custom_rate * quantity
            
            pricing = self.pricing.get(service_type, {})
            
            if service_type == "voice_processing" and duration:
                cost_per_minute = Decimal(str(pricing.get("per_minute", 10)))
                minutes = Decimal(str(duration)) / Decimal("60")
                return cost_per_minute * minutes * Decimal(str(quantity))
            
            elif service_type == "chat_processing":
                cost_per_message = Decimal(str(pricing.get("per_message", 1)))
                return cost_per_message * Decimal(str(quantity))
            
            elif service_type == "face_processing":
                cost_per_image = Decimal(str(pricing.get("per_image", 5)))
                return cost_per_image * Decimal(str(quantity))
            
            elif service_type == "storage":
                cost_per_gb = Decimal(str(pricing.get("per_gb_per_month", 100)))
                return cost_per_gb * Decimal(str(quantity))
            
            elif service_type == "tasks":
                cost_per_execution = Decimal(str(pricing.get("per_task_execution", 5)))
                return cost_per_execution * Decimal(str(quantity))
            
            else:
                return Decimal("0")
                
        except Exception as e:
            logger.error(f"Failed to calculate service cost: {e}")
            return Decimal("0")
    
    async def generate_deferred_invoice(
        self,
        user_id: uuid.UUID,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> Dict[str, Any]:
        """Generate deferred payment invoice for user"""
        try:
            user = await self.db.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Determine billing period
            if not period_start or not period_end:
                period_start, period_end = self._calculate_billing_period(user)
            
            # Calculate usage for period
            usage = await self._calculate_period_usage(user_id, period_start, period_end)
            
            # Calculate total amount
            total_amount = Decimal(str(user.deferred_payment_balance))
            
            # Check minimum amount
            if total_amount < Decimal(str(settings.MIN_DEFERRED_AMOUNT)):
                return {
                    "success": False,
                    "error": f"Minimum amount not reached. Minimum: {settings.MIN_DEFERRED_AMOUNT}",
                    "current_balance": float(total_amount)
                }
            
            # Create invoice
            invoice_number = self._generate_invoice_number()
            payment_due_date = period_end + timedelta(days=settings.DEFERRED_PAYMENT_GRACE_DAYS)
            
            invoice = DeferredPayment(
                id=uuid.uuid4(),
                user_id=user_id,
                invoice_number=invoice_number,
                total_amount=float(total_amount),
                currency=settings.DEFAULT_CURRENCY,
                description=f"Invoice for services from {period_start} to {period_end}",
                billing_period_start=period_start,
                billing_period_end=period_end,
                usage_summary=usage,
                status="pending",
                payment_due_date=payment_due_date
            )
            
            # Reset user's deferred balance
            user.deferred_payment_balance = 0.0
            user.next_payment_due_date = payment_due_date
            
            self.db.add(invoice)
            await self.db.commit()
            
            logger.info(f"Generated invoice {invoice_number} for user {user_id}")
            
            # Send invoice email
            await self.email_service.send_invoice_email(
                email=user.email,
                name=user.full_name or user.username,
                invoice_number=invoice_number,
                amount=float(total_amount),
                currency=settings.DEFAULT_CURRENCY,
                due_date=payment_due_date,
                period_start=period_start,
                period_end=period_end
            )
            
            return {
                "success": True,
                "invoice_id": invoice.id,
                "invoice_number": invoice_number,
                "amount": float(total_amount),
                "currency": settings.DEFAULT_CURRENCY,
                "due_date": payment_due_date,
                "period": f"{period_start} to {period_end}"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to generate invoice: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_outstanding_invoices(
        self,
        user_id: uuid.UUID,
        include_paid: bool = False
    ) -> List[Dict[str, Any]]:
        """Get user's outstanding invoices"""
        try:
            stmt = select(DeferredPayment).where(
                DeferredPayment.user_id == user_id
            )
            
            if not include_paid:
                stmt = stmt.where(
                    DeferredPayment.status.in_(["pending", "overdue"])
                )
            
            stmt = stmt.order_by(DeferredPayment.payment_due_date)
            
            result = await self.db.execute(stmt)
            invoices = result.scalars().all()
            
            return [
                {
                    "invoice_id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "amount": inv.total_amount,
                    "currency": inv.currency,
                    "status": inv.status,
                    "due_date": inv.payment_due_date,
                    "period": f"{inv.billing_period_start} to {inv.billing_period_end}",
                    "days_overdue": inv.overdue_days,
                    "late_fee": inv.late_fee
                }
                for inv in invoices
            ]
            
        except Exception as e:
            logger.error(f"Failed to get invoices: {e}")
            return []
    
    async def process_payment(
        self,
        invoice_id: uuid.UUID,
        payment_method: str,
        payment_reference: str,
        amount: float,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """Process payment for invoice"""
        try:
            # Get invoice
            invoice = await self.db.get(DeferredPayment, invoice_id)
            if not invoice:
                return {"success": False, "error": "Invoice not found"}
            
            # Convert amount to invoice currency if needed
            if currency != invoice.currency:
                converted_amount = await convert_currency(
                    amount=amount,
                    from_currency=currency,
                    to_currency=invoice.currency
                )
            else:
                converted_amount = amount
            
            # Check if amount matches
            if abs(converted_amount - invoice.total_amount) > 0.01:
                return {
                    "success": False,
                    "error": f"Amount mismatch. Expected: {invoice.total_amount} {invoice.currency}, Got: {converted_amount} {invoice.currency}"
                }
            
            # Update invoice
            invoice.status = "paid"
            invoice.payment_date = date.today()
            invoice.payment_method = payment_method
            invoice.payment_reference = payment_reference
            invoice.paid_at = datetime.utcnow()
            
            # Create credit transaction
            transaction = CreditTransaction(
                id=uuid.uuid4(),
                user_id=invoice.user_id,
                transaction_type="payment",
                amount=invoice.total_amount,
                payment_method=payment_method,
                payment_reference=payment_reference,
                status="completed",
                description=f"Payment for invoice {invoice.invoice_number}"
            )
            
            self.db.add(transaction)
            await self.db.commit()
            
            logger.info(f"Processed payment for invoice {invoice.invoice_number}")
            
            # Send payment confirmation
            user = await self.db.get(User, invoice.user_id)
            if user:
                await self.email_service.send_payment_confirmation(
                    email=user.email,
                    name=user.full_name or user.username,
                    invoice_number=invoice.invoice_number,
                    amount=invoice.total_amount,
                    currency=invoice.currency,
                    payment_method=payment_method,
                    payment_date=date.today()
                )
            
            return {
                "success": True,
                "invoice_number": invoice.invoice_number,
                "amount_paid": invoice.total_amount,
                "currency": invoice.currency,
                "payment_date": date.today(),
                "status": "paid"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to process payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_overdue_invoices(self):
        """Check and update overdue invoices"""
        try:
            today = date.today()
            
            # Get pending invoices past due date
            stmt = select(DeferredPayment).where(
                and_(
                    DeferredPayment.status == "pending",
                    DeferredPayment.payment_due_date < today
                )
            )
            
            result = await self.db.execute(stmt)
            invoices = result.scalars().all()
            
            for invoice in invoices:
                # Calculate overdue days
                overdue_days = (today - invoice.payment_due_date).days
                invoice.overdue_days = overdue_days
                invoice.is_overdue = True
                invoice.status = "overdue"
                
                # Apply late fee if overdue more than 7 days
                if overdue_days > 7:
                    late_fee = invoice.total_amount * (settings.LATE_FEE_PERCENTAGE / 100)
                    invoice.late_fee = late_fee
                    invoice.total_amount += late_fee
                
                # Send overdue reminder every 7 days
                if overdue_days % 7 == 0:
                    user = await self.db.get(User, invoice.user_id)
                    if user:
                        await self.email_service.send_overdue_reminder(
                            email=user.email,
                            name=user.full_name or user.username,
                            invoice_number=invoice.invoice_number,
                            amount=invoice.total_amount,
                            currency=invoice.currency,
                            overdue_days=overdue_days,
                            due_date=invoice.payment_due_date
                        )
            
            await self.db.commit()
            logger.info(f"Checked {len(invoices)} overdue invoices")
            
        except Exception as e:
            logger.error(f"Failed to check overdue invoices: {e}")
    
    async def get_billing_history(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's billing history"""
        try:
            # Get transactions
            stmt = select(CreditTransaction).where(
                CreditTransaction.user_id == user_id
            ).order_by(
                CreditTransaction.created_at.desc()
            ).limit(limit).offset(offset)
            
            result = await self.db.execute(stmt)
            transactions = result.scalars().all()
            
            # Get total count
            count_stmt = select(func.count()).select_from(CreditTransaction).where(
                CreditTransaction.user_id == user_id
            )
            count_result = await self.db.execute(count_stmt)
            total_count = count_result.scalar()
            
            # Get invoices
            invoices = await self.get_outstanding_invoices(user_id, include_paid=True)
            
            return {
                "transactions": [
                    {
                        "id": txn.id,
                        "type": txn.transaction_type,
                        "amount": txn.amount,
                        "credits_granted": txn.credits_granted,
                        "credits_used": txn.credits_used,
                        "service_type": txn.service_type,
                        "description": txn.description,
                        "created_at": txn.created_at,
                        "status": txn.status
                    }
                    for txn in transactions
                ],
                "invoices": invoices,
                "total_transactions": total_count,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get billing history: {e}")
            return {"transactions": [], "invoices": [], "total_transactions": 0}
    
    async def estimate_monthly_cost(
        self,
        user_id: uuid.UUID,
        based_on_period: int = 30  # days
    ) -> Dict[str, Any]:
        """Estimate monthly cost based on usage patterns"""
        try:
            # Get usage for the last N days
            period_start = datetime.utcnow() - timedelta(days=based_on_period)
            
            stmt = select(CreditTransaction).where(
                and_(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.transaction_type == "usage",
                    CreditTransaction.created_at >= period_start
                )
            )
            
            result = await self.db.execute(stmt)
            transactions = result.scalars().all()
            
            # Calculate total cost
            total_cost = sum(txn.total_price for txn in transactions)
            
            # Project to monthly
            daily_average = total_cost / based_on_period
            monthly_estimate = daily_average * 30
            
            # Breakdown by service
            breakdown = {}
            for txn in transactions:
                service = txn.service_type or "other"
                breakdown[service] = breakdown.get(service, 0) + txn.total_price
            
            return {
                "period_days": based_on_period,
                "actual_cost": total_cost,
                "daily_average": daily_average,
                "monthly_estimate": monthly_estimate,
                "breakdown": breakdown,
                "currency": settings.DEFAULT_CURRENCY
            }
            
        except Exception as e:
            logger.error(f"Failed to estimate monthly cost: {e}")
            return {"error": str(e)}
    
    def _is_trial_active(self, user: User) -> bool:
        """Check if user is in active trial period"""
        if not user.trial_end_date:
            return False
        return datetime.utcnow().date() <= user.trial_end_date
    
    def _get_billing_period_start(self, user: User) -> date:
        """Get start date of current billing period"""
        if user.last_payment_date:
            return user.last_payment_date
        elif user.trial_end_date:
            return user.trial_end_date + timedelta(days=1)
        else:
            return user.created_at.date()
    
    def _calculate_billing_period(self, user: User) -> Tuple[date, date]:
        """Calculate billing period dates"""
        period_start = self._get_billing_period_start(user)
        period_end = date.today() - timedelta(days=1)  # Yesterday
        
        return period_start, period_end
    
    async def _calculate_period_usage(
        self, 
        user_id: uuid.UUID, 
        period_start: date,
        period_end: Optional[date] = None
    ) -> Dict[str, Any]:
        """Calculate usage for a period"""
        if period_end is None:
            period_end = date.today()
        
        stmt = select(CreditTransaction).where(
            and_(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type == "usage",
                func.date(CreditTransaction.created_at) >= period_start,
                func.date(CreditTransaction.created_at) <= period_end
            )
        )
        
        result = await self.db.execute(stmt)
        transactions = result.scalars().all()
        
        total_cost = sum(txn.total_price for txn in transactions)
        total_credits = sum(txn.credits_used or 0 for txn in transactions)
        
        # Group by service
        by_service = {}
        for txn in transactions:
            service = txn.service_type or "other"
            if service not in by_service:
                by_service[service] = {
                    "cost": 0,
                    "credits": 0,
                    "transactions": 0
                }
            by_service[service]["cost"] += txn.total_price
            by_service[service]["credits"] += txn.credits_used or 0
            by_service[service]["transactions"] += 1
        
        return {
            "period_start": period_start,
            "period_end": period_end,
            "total_cost": total_cost,
            "total_credits": total_credits,
            "by_service": by_service,
            "transaction_count": len(transactions)
        }
    
    async def _calculate_deferred_balance(self, user_id: uuid.UUID) -> float:
        """Calculate total deferred balance including pending invoices"""
        user = await self.db.get(User, user_id)
        if not user:
            return 0.0
        
        # Get unpaid invoices
        stmt = select(func.sum(DeferredPayment.total_amount)).where(
            and_(
                DeferredPayment.user_id == user_id,
                DeferredPayment.status.in_(["pending", "overdue"])
            )
        )
        
        result = await self.db.execute(stmt)
        invoice_balance = result.scalar() or 0.0
        
        return user.deferred_payment_balance + invoice_balance
    
    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_part = str(uuid.uuid4().int)[:6]
        return f"INV-{timestamp}-{random_part}"