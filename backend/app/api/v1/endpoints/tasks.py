"""
Scheduled Tasks API Endpoints
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid
from datetime import datetime, date

from app.schemas.tasks import (
    ScheduledTaskCreate, ScheduledTaskResponse, ScheduledTaskUpdate,
    TaskExecutionResponse, TaskListResponse
)
from app.services.task_service import TaskService
from app.database.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.digital_twin import DigitalTwin

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/create", response_model=ScheduledTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new scheduled task
    """
    try:
        task_service = TaskService(db)
        
        # Get digital twin
        twin = await task_service.get_digital_twin(task_data.twin_id)
        if not twin or twin.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital twin not found"
            )
        
        # Check task limit based on subscription
        task_count = await task_service.get_user_task_count(current_user.id)
        max_tasks = task_service.get_max_tasks_for_user(current_user)
        
        if task_count >= max_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You can only create {max_tasks} scheduled tasks with your current plan"
            )
        
        # Validate schedule
        if not task_service.validate_schedule(task_data):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid schedule configuration"
            )
        
        # Create task
        task = await task_service.create_scheduled_task(
            user_id=current_user.id,
            twin_id=task_data.twin_id,
            task_data=task_data
        )
        
        # Schedule the task
        background_tasks.add_task(
            task_service.schedule_task_execution,
            task_id=task.id
        )
        
        logger.info(f"Scheduled task created: {task.id} for twin: {task_data.twin_id}")
        
        return ScheduledTaskResponse.from_orm(task)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create scheduled task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create scheduled task"
        )

@router.get("/", response_model=TaskListResponse)
async def get_scheduled_tasks(
    twin_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get scheduled tasks for current user
    """
    try:
        task_service = TaskService(db)
        
        tasks = await task_service.get_user_scheduled_tasks(
            user_id=current_user.id,
            twin_id=twin_id,
            status_filter=status_filter,
            skip=skip,
            limit=limit
        )
        
        total = await task_service.get_user_task_count(
            user_id=current_user.id,
            twin_id=twin_id,
            status_filter=status_filter
        )
        
        return TaskListResponse(
            tasks=[ScheduledTaskResponse.from_orm(task) for task in tasks],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Failed to get scheduled tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get scheduled tasks"
        )

@router.get("/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get specific scheduled task
    """
    try:
        task_service = TaskService(db)
        
        task = await task_service.get_scheduled_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found"
            )
        
        # Check ownership
        if task.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this task"
            )
        
        return ScheduledTaskResponse.from_orm(task)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scheduled task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get scheduled task"
        )

@router.put("/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: uuid.UUID,
    task_update: ScheduledTaskUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update scheduled task
    """
    try:
        task_service = TaskService(db)
        
        task = await task_service.get_scheduled_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found"
            )
        
        # Check ownership
        if task.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this task"
            )
        
        # Update task
        updated_task = await task_service.update_scheduled_task(
            task_id=task_id,
            task_update=task_update
        )
        
        # Reschedule if needed
        if task_update.status == "active" and task.status != "active":
            background_tasks.add_task(
                task_service.schedule_task_execution,
                task_id=task_id
            )
        
        logger.info(f"Scheduled task updated: {task_id}")
        
        return ScheduledTaskResponse.from_orm(updated_task)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update scheduled task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update scheduled task"
        )

@router.delete("/{task_id}")
async def delete_scheduled_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete scheduled task
    """
    try:
        task_service = TaskService(db)
        
        task = await task_service.get_scheduled_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found"
            )
        
        # Check ownership
        if task.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this task"
            )
        
        # Delete task
        await task_service.delete_scheduled_task(task_id)
        
        logger.info(f"Scheduled task deleted: {task_id}")
        
        return {
            "success": True,
            "message": "Scheduled task deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete scheduled task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete scheduled task"
        )

@router.post("/{task_id}/execute")
async def execute_task_now(
    task_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Execute scheduled task immediately
    """
    try:
        task_service = TaskService(db)
        
        task = await task_service.get_scheduled_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found"
            )
        
        # Check ownership
        if task.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to execute this task"
            )
        
        # Execute immediately
        background_tasks.add_task(
            task_service.execute_task,
            task_id=task_id,
            manual=True
        )
        
        logger.info(f"Scheduled task executed manually: {task_id}")
        
        return {
            "success": True,
            "message": "Task execution started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute task"
        )

@router.post("/{task_id}/pause")
async def pause_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Pause a scheduled task
    """
    try:
        task_service = TaskService(db)
        
        task = await task_service.get_scheduled_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found"
            )
        
        # Check ownership
        if task.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to pause this task"
            )
        
        # Pause task
        await task_service.pause_task(task_id)
        
        logger.info(f"Scheduled task paused: {task_id}")
        
        return {
            "success": True,
            "message": "Task paused successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause task"
        )

@router.post("/{task_id}/resume")
async def resume_task(
    task_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Resume a paused task
    """
    try:
        task_service = TaskService(db)
        
        task = await task_service.get_scheduled_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found"
            )
        
        # Check ownership
        if task.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to resume this task"
            )
        
        # Resume task
        await task_service.resume_task(task_id)
        
        # Reschedule
        background_tasks.add_task(
            task_service.schedule_task_execution,
            task_id=task_id
        )
        
        logger.info(f"Scheduled task resumed: {task_id}")
        
        return {
            "success": True,
            "message": "Task resumed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume task"
        )

@router.get("/{task_id}/executions")
async def get_task_executions(
    task_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get execution history for a task
    """
    try:
        task_service = TaskService(db)
        
        task = await task_service.get_scheduled_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found"
            )
        
        # Check ownership
        if task.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view executions for this task"
            )
        
        # Get executions
        executions = await task_service.get_task_executions(
            task_id=task_id,
            skip=skip,
            limit=limit
        )
        
        total = await task_service.get_execution_count(task_id)
        
        return {
            "task_id": task_id,
            "task_title": task.title,
            "executions": [TaskExecutionResponse.from_orm(exec) for exec in executions],
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task executions"
        )

@router.get("/upcoming")
async def get_upcoming_tasks(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get upcoming scheduled tasks
    """
    try:
        task_service = TaskService(db)
        
        upcoming_tasks = await task_service.get_upcoming_tasks(
            user_id=current_user.id,
            days=days
        )
        
        return {
            "user_id": current_user.id,
            "period_days": days,
            "upcoming_tasks": upcoming_tasks,
            "count": len(upcoming_tasks)
        }
        
    except Exception as e:
        logger.error(f"Failed to get upcoming tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get upcoming tasks"
        )

@router.get("/analytics")
async def get_task_analytics(
    period: str = "month",  # week, month, year
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get task execution analytics
    """
    try:
        task_service = TaskService(db)
        
        analytics = await task_service.get_task_analytics(
            user_id=current_user.id,
            period=period
        )
        
        return {
            "user_id": current_user.id,
            "period": period,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(f"Failed to get task analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task analytics"
        )

@router.post("/batch/create")
async def create_batch_tasks(
    tasks_data: List[ScheduledTaskCreate],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create multiple scheduled tasks at once
    """
    try:
        task_service = TaskService(db)
        
        created_tasks = []
        failed_tasks = []
        
        for task_data in tasks_data:
            try:
                # Get digital twin
                twin = await task_service.get_digital_twin(task_data.twin_id)
                if not twin or twin.user_id != current_user.id:
                    failed_tasks.append({
                        "twin_id": str(task_data.twin_id),
                        "error": "Digital twin not found or not owned by user"
                    })
                    continue
                
                # Create task
                task = await task_service.create_scheduled_task(
                    user_id=current_user.id,
                    twin_id=task_data.twin_id,
                    task_data=task_data
                )
                
                # Schedule the task
                background_tasks.add_task(
                    task_service.schedule_task_execution,
                    task_id=task.id
                )
                
                created_tasks.append(ScheduledTaskResponse.from_orm(task))
                
            except Exception as e:
                failed_tasks.append({
                    "twin_id": str(task_data.twin_id),
                    "title": task_data.title,
                    "error": str(e)
                })
        
        logger.info(f"Batch created {len(created_tasks)} tasks, failed {len(failed_tasks)}")
        
        return {
            "success": True,
            "created": len(created_tasks),
            "failed": len(failed_tasks),
            "tasks": created_tasks,
            "failures": failed_tasks
        }
        
    except Exception as e:
        logger.error(f"Failed to create batch tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create batch tasks"
        )