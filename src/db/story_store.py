import uuid
import logging
from datetime import datetime
from typing import List, Dict

from .memory import get_mysql_connection

logger = logging.getLogger(__name__)

TABLE_DDL = """
CREATE TABLE IF NOT EXISTS stories (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(100) NOT NULL,
    tags VARCHAR(500) DEFAULT '',
    content TEXT NOT NULL,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TINYINT DEFAULT 0,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def _ensure_table():
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(TABLE_DDL)
        conn.commit()
    except Exception as e:
        logger.warning("Failed to ensure stories table: %s", e)
    finally:
        conn.close()


_ensure_table()


def save_story(title: str, author: str, tags: str, content: str) -> str:
    story_id = str(uuid.uuid4())
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO stories (id, title, author, tags, content, collected_at, status) "
                "VALUES (%s, %s, %s, %s, %s, %s, 0)",
                (story_id, title, author, tags, content, datetime.now()),
            )
        conn.commit()
        logger.info("Saved story %s to MySQL", story_id)
        return story_id
    except Exception as e:
        logger.error("Failed to save story: %s", e)
        return ""
    finally:
        conn.close()


def query_available_stories() -> List[Dict]:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT title, author, tags, collected_at "
                "FROM stories WHERE status = 0 ORDER BY collected_at DESC"
            )
            rows = cursor.fetchall()
        stories = []
        for row in rows:
            stories.append({
                "title": row[0],
                "author": row[1],
                "tags": row[2],
                "collected_at": row[3].strftime("%Y-%m-%d %H:%M") if row[3] else "",
            })
        return stories
    except Exception as e:
        logger.error("Failed to query stories: %s", e)
        return []
    finally:
        conn.close()


def count_available_stories() -> int:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM stories WHERE status = 0")
            row = cursor.fetchone()
        return row[0] if row else 0
    except Exception as e:
        logger.error("Failed to count stories: %s", e)
        return 0
    finally:
        conn.close()