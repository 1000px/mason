import uuid
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict

from .memory import get_mysql_connection

logger = logging.getLogger(__name__)

TABLE_DDL = """
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id VARCHAR(36) PRIMARY KEY,
    run_time DATETIME NOT NULL,
    task_description VARCHAR(500) NOT NULL,
    task_payload JSON,
    status ENUM('pending', 'triggered', 'cancelled') DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status_run_time (status, run_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def _ensure_table():
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(TABLE_DDL)
        conn.commit()
    except Exception as e:
        logger.warning("Failed to ensure scheduled_tasks table: %s", e)
    finally:
        conn.close()


_ensure_table()


def save_task(run_time: datetime, task_description: str, task_payload: dict) -> str:
    task_id = str(uuid.uuid4())
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO scheduled_tasks (id, run_time, task_description, task_payload, status) "
                "VALUES (%s, %s, %s, %s, 'pending')",
                (task_id, run_time, task_description, json.dumps(task_payload, ensure_ascii=False)),
            )
        conn.commit()
        logger.info("Saved task %s to MySQL", task_id)
        return task_id
    except Exception as e:
        logger.error("Failed to save task: %s", e)
        return ""
    finally:
        conn.close()


def mark_triggered(task_id: str):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE scheduled_tasks SET status = 'triggered' WHERE id = %s",
                (task_id,),
            )
        conn.commit()
    except Exception as e:
        logger.error("Failed to mark task %s as triggered: %s", task_id, e)
    finally:
        conn.close()


def cancel_task(task_id: str) -> bool:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE scheduled_tasks SET status = 'cancelled' WHERE id = %s AND status = 'pending'",
                (task_id,),
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "UPDATE scheduled_tasks SET status = 'cancelled' "
                    "WHERE id LIKE %s AND status = 'pending'",
                    (task_id + "%",),
                )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error("Failed to cancel task %s: %s", task_id, e)
        return False
    finally:
        conn.close()


def load_pending_tasks() -> List[Dict]:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, run_time, task_description, task_payload "
                "FROM scheduled_tasks WHERE status = 'pending' AND run_time > NOW()"
            )
            rows = cursor.fetchall()
        tasks = []
        for row in rows:
            payload = row[3]
            if isinstance(payload, str):
                payload = json.loads(payload)
            tasks.append({
                "id": row[0],
                "run_time": row[1],
                "task_description": row[2],
                "task_payload": payload,
            })
        logger.info("Loaded %d pending tasks from MySQL", len(tasks))
        return tasks
    except Exception as e:
        logger.error("Failed to load pending tasks: %s", e)
        return []
    finally:
        conn.close()


def delete_task(task_id: str):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM scheduled_tasks WHERE id = %s", (task_id,))
        conn.commit()
    except Exception as e:
        logger.error("Failed to delete task %s: %s", task_id, e)
    finally:
        conn.close()