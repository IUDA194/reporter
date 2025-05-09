import re

from app.schemas import TaskInput

def enrich_task(task: TaskInput) -> dict:
    match = re.search(r'/t/([a-zA-Z0-9]+)', str(task.url))
    task_id = match.group(1) if match else "unknown"
    return {
        "url": str(task.url),
        "description": task.description,
        "task_id": task_id,
        "task_name": f"TASK {task_id}",
    }