from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas.task_schema import Task
from auth.auth_dependency import check_current_user, admin_obj
from exceptions.custom_exception import raise_not_found_error

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/")
def create_tasks(task: Task, db: Session = Depends(get_db), current_user: dict = Depends(check_current_user)):
    new_task = models.Task(title=task.title, description=task.description, owner_id=current_user["userId"])
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("/")
def get_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(check_current_user)
):
    query = db.query(models.Task).filter(models.Task.owner_id == current_user["userId"])
    total = query.count()
    tasks = query.offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "task": tasks
    }


@router.get("/{task_id}")
def get_task_by_id(task_id: int, current_user: dict = Depends(check_current_user), db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise_not_found_error("Task", task_id)
    if task.owner_id != current_user["userId"]:
        raise HTTPException(status_code=403, detail="Unauthorized...")
    return task


@router.put("/{task_id}")
def update_task_by_id(task_id: int, task: Task, current_user: dict = Depends(check_current_user), db: Session = Depends(get_db)):
    update_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not update_task:
        raise_not_found_error("Task", task_id)
    if update_task.owner_id != current_user["userId"]:
        raise HTTPException(status_code=403, detail="unauthorized")

    update_task.title = task.title
    update_task.description = task.description
    db.commit()
    db.refresh(update_task)
    return update_task


@router.delete("/{task_id}")
def delete_task_by_id(task_id: int, current_user: dict = Depends(check_current_user), db: Session = Depends(get_db)):
    delete_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not delete_task:
        raise_not_found_error("Task", task_id)
    if delete_task.owner_id != current_user["userId"]:
        raise HTTPException(status_code=403, detail="unauthorized")

    db.delete(delete_task)
    db.commit()
    return {"message": "task successfully deleted"}


@router.get("/admin/all-tasks")
def get_all_tasks(db: Session = Depends(get_db), current_user: dict = Depends(admin_obj)):
    return db.query(models.Task).all()