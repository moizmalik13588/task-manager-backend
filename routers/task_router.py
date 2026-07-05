from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas.task_schema import Task
from auth.auth_dependency import check_current_user, admin_obj
from exceptions.custom_exception import raise_not_found_error
import redis
import json
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
router = APIRouter(prefix="/tasks", tags=["Tasks"], redirect_slashes=False)


@router.post("/")
def create_tasks(task: Task, db: Session = Depends(get_db), current_user: dict = Depends(check_current_user)):
    new_task = models.Task(title=task.title, description=task.description, owner_id=current_user["userId"])
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    r.delete("all_tasks")
    r.delete(f"user_tasks:{current_user['userId']}")
    return new_task


@router.get("/")
def get_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(check_current_user)
):
    
    cache_key = f"user_tasks:{current_user["userId"]}"
    cached_data = r.get(cache_key)
    if cached_data:
        print("cache hit")
        all_tasks = json.loads(cached_data)
    else:
        print("cache miss")
        query = db.query(models.Task).filter(models.Task.owner_id == current_user["userId"])
        all_tasks = [
            { "id": t.id, "title": t.title,"description": t.description, "owner_id": t.owner_id }
            for t in query
        ]
        r.set(cache_key, json.dumps(all_tasks), ex=60)
        
    total = len(all_tasks)
    paginated_tasks = all_tasks[skip: skip + limit]
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "task": paginated_tasks
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
    cache_key = "all_tasks"
    
    # 1. Pehle Redis mein check karo — kya cached data hai?
    cached_data = r.get(cache_key)
    if cached_data:
        print("Cache HIT — Redis se data diya")
        return json.loads(cached_data)   # string ko wapas Python object mein convert karo
    
    # 2. Agar cache mein nahi hai, DB se lo
    print("Cache MISS — Database se data liya")
    tasks = db.query(models.Task).all()
    
    # 3. Result ko JSON-serializable format mein convert karo, Redis mein save karo
    tasks_data = [
        {"id": t.id, "title": t.title, "description": t.description, "owner_id": t.owner_id}
        for t in tasks
    ]
    r.set(cache_key, json.dumps(tasks_data), ex=60)   # 60 second ke liye cache karo
    
    return tasks_data