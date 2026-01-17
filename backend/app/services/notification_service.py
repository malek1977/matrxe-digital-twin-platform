"""
Notification Service for MATRXe
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import json
import asyncio

from app.models.notification import Notification
from app.models.user import User
from app.services.email_service import EmailService
from app.services.sms_service import SMSService
from app.services.websocket_service import WebSocketService
from app.core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Service for managing user notifications
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()
        self.sms_service = SMSService()
        self.websocket_service = WebSocketService()
        
        # Notification templates
        self.templates = {
            "welcome": {
                "title": {
                    "ar": "مرحباً بك في ماتركس إي!",
                    "en": "Welcome to MATRXe!"
                },
                "message": {
                    "ar": "نحن سعداء بانضمامك إلى منصتنا للنسخ الرقمية الذكية.",
                    "en": "We're excited to have you join our intelligent digital twin platform."
                }
            },
            "twin_trained": {
                "title": {
                    "ar": "تم تدريب نسختك الرقمية!",
                    "en": "Your digital twin is trained!"
                },
                "message": {
                    "ar": "تم الانتهاء من تدريب نسختك الرقمية '{twin_name}' وهي جاهزة للاستخدام.",
                    "en": "Your digital twin '{twin_name}' has finished training and is ready to use."
                }
            },
            "twin_training_failed": {
                "title": {
                    "ar": "فشل تدريب النسخة الرقمية",
                    "en": "Digital twin training failed"
                },
                "message": {
                    "ar": "فشل تدريب نسختك الرقمية '{twin_name}'. الرجاء المحاولة مرة أخرى.",
                    "en": "Training failed for your digital twin '{twin_name}'. Please try again."
                }
            },
            "task_executed": {
                "title": {
                    "ar": "تم تنفيذ المهمة المجدولة",
                    "en": "Scheduled task executed"
                },
                "message": {
                    "ar": "تم تنفيذ المهمة '{task_title}' بنجاح.",
                    "en": "Task '{task_title}' has been executed successfully."
                }
            },
            "task_failed": {
                "title": {
                    "ar": "فشل تنفيذ المهمة",
                    "en": "Task execution failed"
                },
                "message": {
                    "ar": "فشل تنفيذ المهمة '{task_title}': {error}",
                    "en": "Task '{task_title}' failed to execute: {error}"
                }
            },
            "credits_low": {
                "title": {
                    "ar": "رصيد الائتمان منخفض",
                    "en": "Low credit balance"
                },
                "message": {
                    "ar": "رصيد الائتمان الخاص بك منخفض ({remaining} رصيد). الرجاء إضافة رصيد.",
                    "en": "Your credit balance is low ({remaining} credits). Please add credits."
                }
            },
            "invoice_generated": {
                "title": {
                    "ar": "تم إنشاء فاتورة جديدة",
                    "en": "New invoice generated"
                },
                "message": {
                    "ar": "تم إنشاء فاتورة برقم {invoice_number} بمبلغ {amount} {currency}.",
                    "en": "Invoice {invoice_number} has been generated for {amount} {currency}."
                }
            },
            "payment_received": {
                "title": {
                    "ar": "تم استلام الدفع",
                    "en": "Payment received"
                },
                "message": {
                    "ar": "تم استلام دفعتك للفاتورة {invoice_number}.",
                    "en": "Your payment for invoice {invoice_number} has been received."
                }
            },
            "payment_overdue": {
                "title": {
                    "ar": "فاتورة متأخرة",
                    "en": "Invoice overdue"
                },
                "message": {
                    "ar": "فاتورتك {invoice_number} متأخرة منذ {days} يوم.",
                    "en": "Your invoice {invoice_number} is {days} days overdue."
                }
            },
            "system_update": {
                "title": {
                    "ar": "تحديث النظام",
                    "en": "System update"
                },
                "message": {
                    "ar": "تم تطبيق تحديثات جديدة على النظام.",
                    "en": "New updates have been applied to the system."
                }
            },
            "security_alert": {
                "title": {
                    "ar": "تنبيه أمني",
                    "en": "Security alert"
                },
                "message": {
                    "ar": "تم اكتشاف نشاط غير معتاد على حسابك.",
                    "en": "Unusual activity detected on your account."
                }
            }
        }
    
    async def send_notification(
        self,
        user_id: uuid.UUID,
        notification_type: str,
        channels: List[str] = None,
        variables: Dict[str, Any] = None,
        priority: str = "normal",
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        scheduled_for: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Send notification to user
        """
        try:
            # Get user
            user = await self.db.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get user's language preference
            user_language = user.language_code or settings.DEFAULT_LANGUAGE
            
            # Get notification template
            template = self.templates.get(notification_type, {})
            if not template:
                return {"success": False, "error": f"Unknown notification type: {notification_type}"}
            
            # Prepare title and message
            title_template = template.get("title", {}).get(user_language) or template.get("title", {}).get("en", "")
            message_template = template.get("message", {}).get(user_language) or template.get("message", {}).get("en", "")
            
            # Replace variables
            title = self._replace_variables(title_template, variables or {})
            message = self._replace_variables(message_template, variables or {})
            
            # Default channels
            if not channels:
                channels = ["in_app", "email"]
            
            # Create notification record
            notification = Notification(
                id=uuid.uuid4(),
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message,
                title_ar=template.get("title", {}).get("ar"),
                message_ar=template.get("message", {}).get("ar"),
                title_en=template.get("title", {}).get("en"),
                message_en=template.get("message", {}).get("en"),
                action_url=action_url,
                action_label=action_label,
                channels=channels,
                priority=priority,
                scheduled_for=scheduled_for,
                sent_at=datetime.utcnow() if not scheduled_for else None
            )
            
            self.db.add(notification)
            await self.db.commit()
            
            # Send through requested channels
            sent_via = []
            
            for channel in channels:
                try:
                    if channel == "email":
                        await self._send_email_notification(user, notification)
                        sent_via.append("email")
                    
                    elif channel == "in_app":
                        await self._send_in_app_notification(user, notification)
                        sent_via.append("in_app")
                    
                    elif channel == "push":
                        await self._send_push_notification(user, notification)
                        sent_via.append("push")
                    
                    elif channel == "sms":
                        await self._send_sms_notification(user, notification)
                        sent_via.append("sms")
                    
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel}: {e}")
            
            # Update notification with sent info
            notification.sent_via = sent_via
            await self.db.commit()
            
            logger.info(f"Notification sent to user {user_id}: {notification_type} via {sent_via}")
            
            return {
                "success": True,
                "notification_id": notification.id,
                "user_id": user_id,
                "type": notification_type,
                "channels": channels,
                "sent_via": sent_via,
                "scheduled": scheduled_for is not None
            }
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def send_bulk_notifications(
        self,
        user_ids: List[uuid.UUID],
        notification_type: str,
        channels: List[str] = None,
        variables_list: List[Dict[str, Any]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Send notifications to multiple users
        """
        try:
            results = []
            
            for i, user_id in enumerate(user_ids):
                variables = variables_list[i] if variables_list and i < len(variables_list) else None
                
                result = await self.send_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    channels=channels,
                    variables=variables,
                    priority=priority
                )
                
                results.append({
                    "user_id": user_id,
                    "success": result.get("success", False),
                    "notification_id": result.get("notification_id"),
                    "error": result.get("error")
                })
            
            successful = [r for r in results if r["success"]]
            failed = [r for r in results if not r["success"]]
            
            return {
                "total": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Failed to send bulk notifications: {e}")
            return {
                "total": len(user_ids),
                "successful": 0,
                "failed": len(user_ids),
                "error": str(e)
            }
    
    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get user's notifications
        """
        try:
            from sqlalchemy import select, func
            
            # Build query
            query = select(Notification).where(Notification.user_id == user_id)
            
            if unread_only:
                query = query.where(Notification.is_read == False)
            
            # Get total count
            count_query = select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id
            )
            if unread_only:
                count_query = count_query.where(Notification.is_read == False)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
            
            # Get paginated results
            query = query.order_by(
                Notification.priority.desc(),
                Notification.created_at.desc()
            ).offset(offset).limit(limit)
            
            result = await self.db.execute(query)
            notifications = result.scalars().all()
            
            return {
                "notifications": [
                    {
                        "id": n.id,
                        "type": n.type,
                        "title": n.title,
                        "message": n.message,
                        "action_url": n.action_url,
                        "action_label": n.action_label,
                        "is_read": n.is_read,
                        "read_at": n.read_at,
                        "priority": n.priority,
                        "channels": n.channels,
                        "sent_via": n.sent_via,
                        "created_at": n.created_at,
                        "scheduled_for": n.scheduled_for,
                        "sent_at": n.sent_at
                    }
                    for n in notifications
                ],
                "total": total,
                "unread_count": await self.get_unread_count(user_id),
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return {"notifications": [], "total": 0, "unread_count": 0, "error": str(e)}
    
    async def mark_as_read(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Mark notification as read
        """
        try:
            notification = await self.db.get(Notification, notification_id)
            
            if not notification or notification.user_id != user_id:
                return False
            
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            
            await self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            await self.db.rollback()
            return False
    
    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """
        Mark all user's notifications as read
        """
        try:
            from sqlalchemy import update
            
            stmt = update(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            ).values(
                is_read=True,
                read_at=datetime.utcnow()
            )
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            updated_count = result.rowcount
            logger.info(f"Marked {updated_count} notifications as read for user {user_id}")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to mark all as read: {e}")
            await self.db.rollback()
            return 0
    
    async def delete_notification(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Delete a notification
        """
        try:
            notification = await self.db.get(Notification, notification_id)
            
            if not notification or notification.user_id != user_id:
                return False
            
            await self.db.delete(notification)
            await self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete notification: {e}")
            await self.db.rollback()
            return False
    
    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """
        Get count of unread notifications for user
        """
        try:
            from sqlalchemy import select, func
            
            stmt = select(func.count()).select_from(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
            
            result = await self.db.execute(stmt)
            count = result.scalar() or 0
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0
    
    async def send_scheduled_notifications(self):
        """
        Send scheduled notifications that are due
        """
        try:
            from sqlalchemy import select
            from datetime import datetime
            
            # Find scheduled notifications that are due
            stmt = select(Notification).where(
                and_(
                    Notification.scheduled_for <= datetime.utcnow(),
                    Notification.sent_at.is_(None),
                    Notification.scheduled_for.isnot(None)
                )
            )
            
            result = await self.db.execute(stmt)
            due_notifications = result.scalars().all()
            
            sent_count = 0
            failed_count = 0
            
            for notification in due_notifications:
                try:
                    # Send notification through channels
                    sent_via = []
                    
                    if "email" in notification.channels:
                        user = await self.db.get(User, notification.user_id)
                        if user:
                            await self._send_email_notification(user, notification)
                            sent_via.append("email")
                    
                    if "in_app" in notification.channels:
                        user = await self.db.get(User, notification.user_id)
                        if user:
                            await self._send_in_app_notification(user, notification)
                            sent_via.append("in_app")
                    
                    # Update notification
                    notification.sent_via = sent_via
                    notification.sent_at = datetime.utcnow()
                    
                    sent_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send scheduled notification {notification.id}: {e}")
                    failed_count += 1
            
            await self.db.commit()
            
            logger.info(f"Sent {sent_count} scheduled notifications, failed: {failed_count}")
            
            return {
                "sent": sent_count,
                "failed": failed_count,
                "total": len(due_notifications)
            }
            
        except Exception as e:
            logger.error(f"Failed to send scheduled notifications: {e}")
            return {"sent": 0, "failed": 0, "error": str(e)}
    
    async def create_custom_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        notification_type: str = "custom",
        channels: List[str] = None,
        priority: str = "normal",
        action_url: Optional[str] = None,
        action_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create custom notification
        """
        try:
            if not channels:
                channels = ["in_app"]
            
            # Create notification
            notification = Notification(
                id=uuid.uuid4(),
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message,
                action_url=action_url,
                action_label=action_label,
                channels=channels,
                priority=priority,
                sent_at=datetime.utcnow()
            )
            
            self.db.add(notification)
            await self.db.commit()
            
            # Send through channels
            user = await self.db.get(User, user_id)
            sent_via = []
            
            for channel in channels:
                try:
                    if channel == "email" and user:
                        await self._send_email_notification(user, notification)
                        sent_via.append("email")
                    
                    elif channel == "in_app" and user:
                        await self._send_in_app_notification(user, notification)
                        sent_via.append("in_app")
                    
                except Exception as e:
                    logger.error(f"Failed to send custom notification via {channel}: {e}")
            
            # Update sent info
            notification.sent_via = sent_via
            await self.db.commit()
            
            return {
                "success": True,
                "notification_id": notification.id,
                "sent_via": sent_via
            }
            
        except Exception as e:
            logger.error(f"Failed to create custom notification: {e}")
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    # Private helper methods
    
    def _replace_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """Replace variables in template string"""
        if not template or not variables:
            return template
        
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        return result
    
    async def _send_email_notification(self, user: User, notification: Notification):
        """Send notification via email"""
        try:
            await self.email_service.send_notification_email(
                email=user.email,
                name=user.full_name or user.username,
                subject=notification.title,
                message=notification.message,
                notification_type=notification.type,
                action_url=notification.action_url,
                action_label=notification.action_label
            )
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            raise
    
    async def _send_in_app_notification(self, user: User, notification: Notification):
        """Send in-app notification via WebSocket"""
        try:
            await self.websocket_service.send_notification(
                user_id=user.id,
                notification={
                    "id": str(notification.id),
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "action_url": notification.action_url,
                    "action_label": notification.action_label,
                    "priority": notification.priority,
                    "created_at": notification.created_at.isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to send in-app notification: {e}")
            # Don't raise - in-app notifications are optional
    
    async def _send_push_notification(self, user: User, notification: Notification):
        """Send push notification (mobile)"""
        try:
            # In production, integrate with Firebase Cloud Messaging or similar
            logger.info(f"Push notification would be sent to user {user.id}")
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            raise
    
    async def _send_sms_notification(self, user: User, notification: Notification):
        """Send SMS notification"""
        try:
            if user.phone:
                await self.sms_service.send_sms(
                    phone_number=user.phone,
                    message=f"{notification.title}: {notification.message}"
                )
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
            raise
    
    async def get_notification_stats(
        self,
        user_id: Optional[uuid.UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get notification statistics
        """
        try:
            from sqlalchemy import select, func, and_
            from datetime import datetime, timedelta
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Build query
            query = select(
                Notification.type,
                func.count(Notification.id).label("total"),
                func.sum(func.cast(Notification.is_read, func.Integer)).label("read"),
                func.avg(
                    func.extract('epoch', Notification.read_at - Notification.created_at)
                ).label("avg_read_time_seconds")
            ).where(
                Notification.created_at >= start_date
            )
            
            if user_id:
                query = query.where(Notification.user_id == user_id)
            
            query = query.group_by(Notification.type)
            
            result = await self.db.execute(query)
            stats_by_type = result.all()
            
            # Calculate totals
            total_stats = {
                "total": sum(s.total for s in stats_by_type),
                "read": sum(s.read or 0 for s in stats_by_type),
                "unread": sum(s.total - (s.read or 0) for s in stats_by_type),
                "read_rate": 0,
                "by_type": {}
            }
            
            for stat in stats_by_type:
                read_rate = (stat.read or 0) / stat.total if stat.total > 0 else 0
                total_stats["by_type"][stat.type] = {
                    "total": stat.total,
                    "read": stat.read or 0,
                    "unread": stat.total - (stat.read or 0),
                    "read_rate": read_rate,
                    "avg_read_time_seconds": stat.avg_read_time_seconds
                }
            
            if total_stats["total"] > 0:
                total_stats["read_rate"] = total_stats["read"] / total_stats["total"]
            
            return {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "stats": total_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            return {"error": str(e)}