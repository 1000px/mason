import pymysql
from langgraph.store.mysql import PyMySQLStore
from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver

# MySQL 连接配置
CONNECTION_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "Root4455",
    "database": "mason",
    "charset": "utf8mb4"
}

def get_mysql_connection():
    """获取 MySQL 连接"""
    return pymysql.connect(**CONNECTION_CONFIG)

def get_checkpointer():
    """短期记忆（Checkpointer）"""
    conn = get_mysql_connection()
    checkpointer = PyMySQLSaver(conn)
    checkpointer.setup()
    return checkpointer

def get_memory_store():
    """长期记忆（Store）"""
    conn = get_mysql_connection()
    store = PyMySQLStore(conn)
    store.setup()
    return store
