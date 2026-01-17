"""
Monitoring and Health Check Service for MATRXe
"""

import logging
import psutil
import socket
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
import redis
import requests
from prometheus_client import Counter, Histogram, Gauge, generate_latest

from app.core.config import settings
from app.database.database import engine
from app.models.user import User
from app.models.digital_twin import DigitalTwin
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'matrxe_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'matrxe_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

ACTIVE_USERS = Gauge(
    'matrxe_active_users',
    'Number of active users'
)

ACTIVE_TWINS = Gauge(
    'matrxe_active_twins',
    'Number of active digital twins'
)

ACTIVE_CONVERSATIONS = Gauge(
    'matrxe_active_conversations',
    'Number of active conversations'
)

DATABASE_CONNECTIONS = Gauge(
    'matrxe_database_connections',
    'Number of database connections'
)

REDIS_MEMORY = Gauge(
    'matrxe_redis_memory_bytes',
    'Redis memory usage in bytes'
)

SYSTEM_CPU = Gauge(
    'matrxe_system_cpu_percent',
    'System CPU usage percentage'
)

SYSTEM_MEMORY = Gauge(
    'matrxe_system_memory_bytes',
    'System memory usage in bytes'
)

SYSTEM_DISK = Gauge(
    'matrxe_system_disk_bytes',
    'System disk usage in bytes'
)

class MonitoringService:
    """
    Service for system monitoring and health checks
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis_client = None
        self.start_time = datetime.utcnow()
        
        # Initialize Redis client
        if settings.REDIS_URL:
            try:
                import redis as redis_client
                self.redis_client = redis_client.from_url(settings.REDIS_URL)
            except Exception as e:
                logger.error(f"Failed to initialize Redis client: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        """
        try:
            checks = {}
            
            # Database health
            checks["database"] = await self._check_database_health()
            
            # Redis health
            checks["redis"] = await self._check_redis_health()
            
            # External services health
            checks["external_services"] = await self._check_external_services()
            
            # System resources
            checks["system_resources"] = await self._check_system_resources()
            
            # Application metrics
            checks["application"] = await self._get_application_metrics()
            
            # Overall status
            all_healthy = all(
                check.get("status") == "healthy" 
                for check in checks.values() 
                if isinstance(check, dict)
            )
            
            overall_status = "healthy" if all_healthy else "degraded"
            
            return {
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": str(datetime.utcnow() - self.start_time),
                "checks": checks
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_metrics(self) -> str:
        """
        Get Prometheus metrics
        """
        try:
            # Update dynamic metrics
            await self._update_metrics()
            
            # Generate metrics
            return generate_latest().decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return ""
    
    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """
        Get detailed system and application metrics
        """
        try:
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "system": await self._get_system_metrics(),
                "database": await self._get_database_metrics(),
                "redis": await self._get_redis_metrics(),
                "application": await self._get_application_metrics(),
                "performance": await self._get_performance_metrics()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get detailed metrics: {e}")
            return {"error": str(e)}
    
    async def monitor_endpoint(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float
    ):
        """
        Monitor API endpoint calls
        """
        try:
            # Update Prometheus metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            # Log to database (optional)
            await self._log_request(method, endpoint, status_code, duration)
            
        except Exception as e:
            logger.error(f"Failed to monitor endpoint: {e}")
    
    async def get_system_alerts(self) -> List[Dict[str, Any]]:
        """
        Get system alerts based on thresholds
        """
        try:
            alerts = []
            
            # Check system resources
            system_metrics = await self._get_system_metrics()
            
            # CPU alert
            if system_metrics.get("cpu_percent", 0) > 80:
                alerts.append({
                    "level": "warning",
                    "type": "high_cpu",
                    "message": f"High CPU usage: {system_metrics['cpu_percent']}%",
                    "value": system_metrics["cpu_percent"],
                    "threshold": 80,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Memory alert
            memory_usage = system_metrics.get("memory", {}).get("percent", 0)
            if memory_usage > 85:
                alerts.append({
                    "level": "warning",
                    "type": "high_memory",
                    "message": f"High memory usage: {memory_usage}%",
                    "value": memory_usage,
                    "threshold": 85,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Disk alert
            disk_usage = system_metrics.get("disk", {}).get("percent", 0)
            if disk_usage > 90:
                alerts.append({
                    "level": "critical",
                    "type": "high_disk",
                    "message": f"High disk usage: {disk_usage}%",
                    "value": disk_usage,
                    "threshold": 90,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Database alert
            db_metrics = await self._get_database_metrics()
            db_connections = db_metrics.get("connections", {}).get("active", 0)
            if db_connections > 50:
                alerts.append({
                    "level": "warning",
                    "type": "high_db_connections",
                    "message": f"High database connections: {db_connections}",
                    "value": db_connections,
                    "threshold": 50,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get system alerts: {e}")
            return []
    
    async def get_performance_report(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get performance report for time period
        """
        try:
            report = {
                "period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "requests": await self._get_request_stats(start_time, end_time),
                "users": await self._get_user_stats(start_time, end_time),
                "twins": await self._get_twin_stats(start_time, end_time),
                "conversations": await self._get_conversation_stats(start_time, end_time),
                "errors": await self._get_error_stats(start_time, end_time)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to get performance report: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            start_time = time.time()
            
            # Test connection
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                await conn.close()
            
            latency = time.time() - start_time
            
            # Get database stats
            stats = await self._get_database_stats()
            
            return {
                "status": "healthy",
                "latency_seconds": round(latency, 3),
                "stats": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            if not self.redis_client:
                return {
                    "status": "disabled",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            start_time = time.time()
            
            # Test connection
            self.redis_client.ping()
            
            latency = time.time() - start_time
            
            # Get Redis info
            info = self.redis_client.info()
            
            return {
                "status": "healthy",
                "latency_seconds": round(latency, 3),
                "connected_clients": info.get('connected_clients', 0),
                "used_memory": info.get('used_memory', 0),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external services health"""
        services = {}
        
        # Check AI services
        ai_services = [
            ("Ollama", f"{settings.OLLAMA_BASE_URL}/api/tags", "GET"),
            ("ElevenLabs", "https://api.elevenlabs.io/v1/voices", "GET"),
            ("Hugging Face", "https://huggingface.co/api/models", "GET")
        ]
        
        for name, url, method in ai_services:
            try:
                start_time = time.time()
                
                response = requests.request(
                    method=method,
                    url=url,
                    timeout=5
                )
                
                latency = time.time() - start_time
                status = "healthy" if response.status_code < 500 else "degraded"
                
                services[name.lower().replace(" ", "_")] = {
                    "status": status,
                    "latency_seconds": round(latency, 3),
                    "status_code": response.status_code
                }
                
            except Exception as e:
                services[name.lower().replace(" ", "_")] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return services
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory
            memory = psutil.virtual_memory()
            
            # Disk
            disk = psutil.disk_usage('/')
            
            # Network
            net_io = psutil.net_io_counters()
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "cores": psutil.cpu_count(logical=False),
                    "threads": psutil.cpu_count(logical=True)
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"System resources check failed: {e}")
            return {"error": str(e)}
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get detailed system metrics"""
        try:
            # Process information
            process = psutil.Process()
            
            metrics = {
                "cpu": {
                    "system_percent": psutil.cpu_percent(interval=0.1),
                    "process_percent": process.cpu_percent(),
                    "cores": psutil.cpu_count(logical=False),
                    "threads": psutil.cpu_count(logical=True)
                },
                "memory": {
                    "system": dict(psutil.virtual_memory()._asdict()),
                    "process": dict(process.memory_info()._asdict()),
                    "process_percent": process.memory_percent()
                },
                "disk": dict(psutil.disk_usage('/')._asdict()),
                "network": dict(psutil.net_io_counters()._asdict()),
                "process": {
                    "pid": process.pid,
                    "name": process.name(),
                    "status": process.status(),
                    "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                    "connections": len(process.connections())
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"error": str(e)}
    
    async def _get_database_metrics(self) -> Dict[str, Any]:
        """Get database metrics"""
        try:
            # Get connection pool stats
            pool = engine.pool
            pool_status = {
                "size": pool.size() if hasattr(pool, 'size') else 0,
                "checkedin": pool.checkedin() if hasattr(pool, 'checkedin') else 0,
                "checkedout": pool.checkedout() if hasattr(pool, 'checkedout') else 0,
                "overflow": pool.overflow() if hasattr(pool, 'overflow') else 0
            }
            
            # Get database size and stats
            async with engine.connect() as conn:
                # Get database size
                size_result = await conn.execute(text("""
                    SELECT pg_database_size(current_database()) as size_bytes
                """))
                db_size = size_result.scalar()
                
                # Get table sizes
                table_sizes = await conn.execute(text("""
                    SELECT 
                        schemaname || '.' || tablename as table_name,
                        pg_total_relation_size(schemaname || '.' || tablename) as size_bytes
                    FROM pg_tables
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY size_bytes DESC
                    LIMIT 10
                """))
                
                tables = [
                    {"name": row[0], "size_bytes": row[1]}
                    for row in table_sizes
                ]
                
                await conn.close()
            
            return {
                "connections": pool_status,
                "database_size": db_size,
                "tables": tables,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get database metrics: {e}")
            return {"error": str(e)}
    
    async def _get_redis_metrics(self) -> Dict[str, Any]:
        """Get Redis metrics"""
        try:
            if not self.redis_client:
                return {"status": "disabled"}
            
            info = self.redis_client.info()
            
            metrics = {
                "clients": {
                    "connected": info.get('connected_clients', 0),
                    "blocked": info.get('blocked_clients', 0)
                },
                "memory": {
                    "used": info.get('used_memory', 0),
                    "peak": info.get('used_memory_peak', 0),
                    "rss": info.get('used_memory_rss', 0),
                    "fragmentation_ratio": info.get('mem_fragmentation_ratio', 0)
                },
                "stats": {
                    "total_connections": info.get('total_connections_received', 0),
                    "total_commands": info.get('total_commands_processed', 0),
                    "instantaneous_ops": info.get('instantaneous_ops_per_sec', 0),
                    "keyspace_hits": info.get('keyspace_hits', 0),
                    "keyspace_misses": info.get('keyspace_misses', 0)
                },
                "keyspace": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get keyspace info
            for db in range(0, 16):
                db_key = f"db{db}"
                if db_key in info:
                    metrics["keyspace"][db_key] = info[db_key]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get Redis metrics: {e}")
            return {"error": str(e)}
    
    async def _get_application_metrics(self) -> Dict[str, Any]:
        """Get application metrics"""
        try:
            # User statistics
            user_stats = await self._get_user_stats(
                datetime.utcnow() - timedelta(days=30),
                datetime.utcnow()
            )
            
            # Twin statistics
            twin_stats = await self._get_twin_stats(
                datetime.utcnow() - timedelta(days=30),
                datetime.utcnow()
            )
            
            # Conversation statistics
            conversation_stats = await self._get_conversation_stats(
                datetime.utcnow() - timedelta(days=30),
                datetime.utcnow()
            )
            
            return {
                "users": user_stats,
                "twins": twin_stats,
                "conversations": conversation_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get application metrics: {e}")
            return {"error": str(e)}
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        try:
            # Get recent request statistics
            async with engine.connect() as conn:
                # This would query from request logs table
                # For now, return empty metrics
                await conn.close()
            
            return {
                "requests_per_second": 0,
                "average_response_time": 0,
                "error_rate": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}
    
    async def _get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            async with engine.connect() as conn:
                # Get table counts
                tables = ['users', 'digital_twins', 'conversations', 'messages', 'scheduled_tasks']
                counts = {}
                
                for table in tables:
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    counts[table] = result.scalar()
                
                await conn.close()
            
            return counts
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    async def _update_metrics(self):
        """Update Prometheus metrics"""
        try:
            # Update system metrics
            SYSTEM_CPU.set(psutil.cpu_percent())
            
            memory = psutil.virtual_memory()
            SYSTEM_MEMORY.set(memory.used)
            
            disk = psutil.disk_usage('/')
            SYSTEM_DISK.set(disk.used)
            
            # Update application metrics
            user_count = await self._count_users()
            ACTIVE_USERS.set(user_count)
            
            twin_count = await self._count_twins()
            ACTIVE_TWINS.set(twin_count)
            
            conversation_count = await self._count_conversations()
            ACTIVE_CONVERSATIONS.set(conversation_count)
            
            # Update database connections
            if hasattr(engine.pool, 'checkedout'):
                DATABASE_CONNECTIONS.set(engine.pool.checkedout())
            
            # Update Redis memory
            if self.redis_client:
                try:
                    redis_info = self.redis_client.info()
                    REDIS_MEMORY.set(redis_info.get('used_memory', 0))
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
    
    async def _log_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float
    ):
        """Log request to database"""
        # In production, this would insert into a requests_log table
        pass
    
    async def _count_users(self) -> int:
        """Count total users"""
        try:
            stmt = select(func.count(User.id))
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except:
            return 0
    
    async def _count_twins(self) -> int:
        """Count total digital twins"""
        try:
            stmt = select(func.count(DigitalTwin.id))
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except:
            return 0
    
    async def _count_conversations(self) -> int:
        """Count total conversations"""
        try:
            stmt = select(func.count(Conversation.id))
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except:
            return 0
    
    async def _get_request_stats(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get request statistics for period"""
        # In production, query from requests_log table
        return {
            "total": 0,
            "by_method": {},
            "by_endpoint": {},
            "by_status": {},
            "average_duration": 0
        }
    
    async def _get_user_stats(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get user statistics for period"""
        try:
            # Total users
            total_stmt = select(func.count(User.id))
            total_result = await self.db.execute(total_stmt)
            total_users = total_result.scalar() or 0
            
            # New users in period
            new_stmt = select(func.count(User.id)).where(
                User.created_at >= start_time,
                User.created_at <= end_time
            )
            new_result = await self.db.execute(new_stmt)
            new_users = new_result.scalar() or 0
            
            # Active users (logged in within last 7 days)
            active_start = datetime.utcnow() - timedelta(days=7)
            active_stmt = select(func.count(User.id)).where(
                User.last_login >= active_start
            )
            active_result = await self.db.execute(active_stmt)
            active_users = active_result.scalar() or 0
            
            return {
                "total": total_users,
                "new": new_users,
                "active": active_users,
                "growth_rate": new_users / total_users if total_users > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {"error": str(e)}
    
    async def _get_twin_stats(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get digital twin statistics for period"""
        try:
            # Total twins
            total_stmt = select(func.count(DigitalTwin.id))
            total_result = await self.db.execute(total_stmt)
            total_twins = total_result.scalar() or 0
            
            # New twins in period
            new_stmt = select(func.count(DigitalTwin.id)).where(
                DigitalTwin.created_at >= start_time,
                DigitalTwin.created_at <= end_time
            )
            new_result = await self.db.execute(new_stmt)
            new_twins = new_result.scalar() or 0
            
            # Trained twins
            trained_stmt = select(func.count(DigitalTwin.id)).where(
                DigitalTwin.training_status == 'trained'
            )
            trained_result = await self.db.execute(trained_stmt)
            trained_twins = trained_result.scalar() or 0
            
            return {
                "total": total_twins,
                "new": new_twins,
                "trained": trained_twins,
                "training_rate": trained_twins / total_twins if total_twins > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get twin stats: {e}")
            return {"error": str(e)}
    
    async def _get_conversation_stats(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get conversation statistics for period"""
        try:
            # Total conversations
            total_stmt = select(func.count(Conversation.id))
            total_result = await self.db.execute(total_stmt)
            total_conversations = total_result.scalar() or 0
            
            # New conversations in period
            new_stmt = select(func.count(Conversation.id)).where(
                Conversation.created_at >= start_time,
                Conversation.created_at <= end_time
            )
            new_result = await self.db.execute(new_stmt)
            new_conversations = new_result.scalar() or 0
            
            # Active conversations (updated within last 24 hours)
            active_start = datetime.utcnow() - timedelta(hours=24)
            active_stmt = select(func.count(Conversation.id)).where(
                Conversation.updated_at >= active_start
            )
            active_result = await self.db.execute(active_stmt)
            active_conversations = active_result.scalar() or 0
            
            return {
                "total": total_conversations,
                "new": new_conversations,
                "active": active_conversations,
                "messages_per_conversation": 0  # Would calculate from messages table
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation stats: {e}")
            return {"error": str(e)}
    
    async def _get_error_stats(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get error statistics for period"""
        # In production, query from error_logs table
        return {
            "total": 0,
            "by_type": {},
            "by_endpoint": {},
            "rate": 0
        }