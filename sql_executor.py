"""
sql_executor.py - Safe SQL Query Execution
Validates and executes only safe SELECT queries on uploaded SQLite databases.
Blocks all destructive operations.
"""

import sqlite3
import logging
import re
import signal
from config import Config

logger = logging.getLogger(__name__)

# Blocked SQL keywords - any query containing these will be rejected
BLOCKED_KEYWORDS = [
    'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE',
    'CREATE', 'REPLACE', 'ATTACH', 'DETACH', 'PRAGMA',
    'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'SCRIPT',
    'LOAD_EXTENSION', 'COPY', 'VACUUM'
]


def validate_query(query: str) -> tuple[bool, str]:
    """
    Validate that a SQL query is safe to execute.
    Returns (is_safe, error_message).
    """
    if not query or not query.strip():
        return False, "Query is empty"
    
    # Normalize the query - uppercase for checking
    query_upper = query.upper().strip()
    
    # Check for blocked keywords
    for keyword in BLOCKED_KEYWORDS:
        # Word boundary check to avoid false positives
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, query_upper):
            return False, f"Blocked operation: {keyword} is not allowed. Only SELECT queries are permitted."
    
    # Must start with SELECT or WITH (for CTEs)
    if not (query_upper.startswith('SELECT') or query_upper.startswith('WITH')):
        return False, "Only SELECT and WITH (CTE) queries are allowed."
    
    # Check for semicolons that could indicate multiple statements
    # Allow one trailing semicolon but not multiple statements
    cleaned = query.strip().rstrip(';')
    if ';' in cleaned:
        return False, "Multiple SQL statements are not allowed."
    
    return True, ""


def execute_safe_query(db_file_path: str, query: str) -> dict:
    """
    Execute a validated SELECT query on an uploaded SQLite database.
    Returns dict with columns, rows, and row_count.
    """
    # Validate the query first
    is_safe, error_msg = validate_query(query)
    if not is_safe:
        return {
            'success': False,
            'error': error_msg,
            'columns': [],
            'rows': [],
            'row_count': 0
        }
    
    conn = None
    try:
        # Open in read-only mode using URI
        conn = sqlite3.connect(f'file:{db_file_path}?mode=ro', uri=True)
        conn.set_trace_callback(None)  # Disable any trace callbacks
        
        # Set a row limit via rowcount
        cursor = conn.cursor()
        
        # Set timeout
        conn.execute(f"PRAGMA busy_timeout = {Config.QUERY_TIMEOUT * 1000}")
        
        # Add LIMIT if not present to prevent huge result sets
        query_upper = query.upper()
        if 'LIMIT' not in query_upper:
            # Add limit to prevent memory issues
            query = query.rstrip(';') + f' LIMIT {Config.MAX_QUERY_ROWS}'
        
        cursor.execute(query)
        
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(Config.MAX_QUERY_ROWS)
        
        # Convert to JSON-serializable format
        rows_list = []
        for row in rows:
            rows_list.append([str(v) if v is not None else None for v in row])
        
        return {
            'success': True,
            'columns': columns,
            'rows': rows_list,
            'row_count': len(rows_list),
            'limited': len(rows_list) >= Config.MAX_QUERY_ROWS,
            'max_rows': Config.MAX_QUERY_ROWS
        }
    
    except sqlite3.OperationalError as e:
        return {
            'success': False,
            'error': f"SQL Error: {str(e)}",
            'columns': [],
            'rows': [],
            'row_count': 0
        }
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        return {
            'success': False,
            'error': f"Execution error: {str(e)}",
            'columns': [],
            'rows': [],
            'row_count': 0
        }
    finally:
        if conn:
            conn.close()


def get_table_preview(db_file_path: str, table_name: str, limit: int = 50) -> dict:
    """
    Get a preview of rows from a specific table.
    """
    # Sanitize table name to prevent injection
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        return {'success': False, 'error': 'Invalid table name'}
    
    query = f'SELECT * FROM "{table_name}" LIMIT {limit}'
    return execute_safe_query(db_file_path, query)


def get_table_count(db_file_path: str, table_name: str) -> int:
    """Get the row count of a table."""
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        return 0
    
    result = execute_safe_query(db_file_path, f'SELECT COUNT(*) FROM "{table_name}"')
    if result['success'] and result['rows']:
        return int(result['rows'][0][0])
    return 0
