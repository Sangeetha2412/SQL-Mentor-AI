"""
file_processor.py - File Processing and Analysis
Handles reading, parsing, and extracting metadata from all supported file types.
"""

import os
import json
import logging
import sqlite3
import sqlparse
import pandas as pd
import PyPDF2

logger = logging.getLogger(__name__)


def process_file(file_path: str, file_type: str, user_id: int) -> dict:
    """
    Main entry point. Processes a file based on its type.
    Returns metadata dict with analysis results.
    """
    try:
        if file_type in ('csv',):
            return process_csv(file_path)
        elif file_type in ('xlsx', 'xls'):
            return process_excel(file_path)
        elif file_type == 'json':
            return process_json(file_path)
        elif file_type == 'pdf':
            return process_pdf(file_path)
        elif file_type in ('txt', 'md'):
            return process_text(file_path, file_type)
        elif file_type == 'sql':
            return process_sql_file(file_path)
        elif file_type in ('db', 'sqlite', 'sqlite3'):
            return process_sqlite(file_path)
        else:
            return {'type': file_type, 'status': 'unsupported'}
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return {'type': file_type, 'status': 'error', 'error': str(e)}


def process_dataframe(df: pd.DataFrame, file_type: str) -> dict:
    """
    Analyze a pandas DataFrame and return rich metadata.
    Used for CSV, Excel, and JSON tabular data.
    """
    meta = {
        'type': file_type,
        'total_rows': int(len(df)),
        'total_columns': int(len(df.columns)),
        'columns': list(df.columns),
        'dtypes': {col: str(df[col].dtype) for col in df.columns},
        'missing_values': int(df.isnull().sum().sum()),
        'duplicate_rows': int(df.duplicated().sum()),
        'column_stats': {},
        'preview': []
    }
    
    # Per-column stats
    for col in df.columns:
        col_stats = {
            'dtype': str(df[col].dtype),
            'null_count': int(df[col].isnull().sum()),
            'null_pct': round(df[col].isnull().mean() * 100, 2),
            'unique_count': int(df[col].nunique()),
        }
        
        # Numeric column stats
        if pd.api.types.is_numeric_dtype(df[col]):
            col_stats.update({
                'min': float(df[col].min()) if not pd.isna(df[col].min()) else None,
                'max': float(df[col].max()) if not pd.isna(df[col].max()) else None,
                'mean': float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                'median': float(df[col].median()) if not pd.isna(df[col].median()) else None,
                'std': float(df[col].std()) if not pd.isna(df[col].std()) else None,
            })
        else:
            # Categorical column - top values
            top_vals = df[col].value_counts().head(5)
            col_stats['top_values'] = {str(k): int(v) for k, v in top_vals.items()}
        
        meta['column_stats'][col] = col_stats
    
    # Preview: first 50 rows as list of dicts (convert to strings for JSON safety)
    preview_df = df.head(50).fillna('').astype(str)
    meta['preview'] = preview_df.to_dict(orient='records')
    
    return meta


def process_csv(file_path: str) -> dict:
    """Process CSV file using pandas."""
    try:
        # Try different encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        
        meta = process_dataframe(df, 'csv')
        meta['status'] = 'processed'
        return meta
    except Exception as e:
        logger.error(f"CSV processing error: {e}")
        return {'type': 'csv', 'status': 'error', 'error': str(e)}


def process_excel(file_path: str) -> dict:
    """Process Excel file (.xlsx or .xls) using pandas."""
    try:
        # Get sheet names first
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
        
        # Read the first sheet
        df = pd.read_excel(file_path, sheet_name=0)
        
        meta = process_dataframe(df, 'excel')
        meta['sheet_names'] = sheet_names
        meta['active_sheet'] = sheet_names[0] if sheet_names else 'Sheet1'
        meta['status'] = 'processed'
        return meta
    except Exception as e:
        logger.error(f"Excel processing error: {e}")
        return {'type': 'excel', 'status': 'error', 'error': str(e)}


def process_json(file_path: str) -> dict:
    """Process JSON file - handles both array and object formats."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        meta = {'type': 'json', 'raw_type': type(data).__name__}
        
        if isinstance(data, list):
            # Array of objects - convert to DataFrame
            df = pd.json_normalize(data)
            meta.update(process_dataframe(df, 'json'))
        elif isinstance(data, dict):
            # Check if it has a list value we can use
            list_keys = [k for k, v in data.items() if isinstance(v, list)]
            if list_keys:
                df = pd.json_normalize(data[list_keys[0]])
                meta.update(process_dataframe(df, 'json'))
                meta['data_key'] = list_keys[0]
            else:
                meta['keys'] = list(data.keys())
                meta['total_keys'] = len(data)
                meta['preview'] = [{k: str(v)[:100] for k, v in data.items()}]
        
        meta['status'] = 'processed'
        return meta
    except Exception as e:
        logger.error(f"JSON processing error: {e}")
        return {'type': 'json', 'status': 'error', 'error': str(e)}


def process_pdf(file_path: str) -> dict:
    """Extract text from PDF files."""
    try:
        text_content = []
        page_count = 0
        
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            page_count = len(reader.pages)
            
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
        
        full_text = '\n'.join(text_content)
        
        meta = {
            'type': 'pdf',
            'page_count': page_count,
            'total_chars': len(full_text),
            'total_words': len(full_text.split()),
            'preview_text': full_text[:500] if full_text else '',
            'extracted_text': full_text,  # Used for RAG embedding
            'status': 'processed'
        }
        return meta
    except Exception as e:
        logger.error(f"PDF processing error: {e}")
        return {'type': 'pdf', 'status': 'error', 'error': str(e)}


def process_text(file_path: str, file_type: str) -> dict:
    """Process TXT or Markdown files."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        meta = {
            'type': file_type,
            'total_chars': len(content),
            'total_words': len(content.split()),
            'total_lines': len(content.splitlines()),
            'preview_text': content[:500],
            'extracted_text': content,  # Used for RAG embedding
            'status': 'processed'
        }
        return meta
    except Exception as e:
        logger.error(f"Text processing error: {e}")
        return {'type': file_type, 'status': 'error', 'error': str(e)}


def process_sql_file(file_path: str) -> dict:
    """
    Parse SQL files to extract schema information.
    Does NOT execute the SQL - only parses it for metadata.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Parse SQL statements
        statements = sqlparse.parse(content)
        
        tables = {}
        create_count = 0
        insert_count = 0
        select_count = 0
        
        for stmt in statements:
            stmt_type = stmt.get_type()
            if stmt_type == 'CREATE':
                create_count += 1
                table_info = _parse_create_table(str(stmt))
                if table_info:
                    tables[table_info['name']] = table_info
            elif stmt_type == 'INSERT':
                insert_count += 1
            elif stmt_type == 'SELECT':
                select_count += 1
        
        meta = {
            'type': 'sql',
            'total_statements': len(statements),
            'create_statements': create_count,
            'insert_statements': insert_count,
            'select_statements': select_count,
            'tables': tables,
            'table_names': list(tables.keys()),
            'extracted_text': content,  # For RAG
            'status': 'processed'
        }
        return meta
    except Exception as e:
        logger.error(f"SQL file processing error: {e}")
        return {'type': 'sql', 'status': 'error', 'error': str(e)}


def _parse_create_table(sql: str) -> dict:
    """Extract table name and columns from a CREATE TABLE statement."""
    try:
        import re
        
        # Extract table name
        table_match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?', 
                                sql, re.IGNORECASE)
        if not table_match:
            return None
        
        table_name = table_match.group(1)
        
        # Extract column definitions (simplified)
        columns = []
        col_pattern = re.findall(r'[`"]?(\w+)[`"]?\s+(VARCHAR|INT|INTEGER|TEXT|REAL|FLOAT|DOUBLE|BOOLEAN|DATE|DATETIME|TIMESTAMP|NUMERIC|DECIMAL|CHAR|BLOB)[^,\n]*', 
                                  sql, re.IGNORECASE)
        for col_name, col_type in col_pattern:
            columns.append({'name': col_name, 'type': col_type.upper()})
        
        # Detect primary keys
        pk_match = re.findall(r'PRIMARY\s+KEY\s*\([`"]?(\w+)[`"]?\)', sql, re.IGNORECASE)
        
        return {
            'name': table_name,
            'columns': columns,
            'primary_keys': pk_match
        }
    except Exception:
        return None


def process_sqlite(file_path: str) -> dict:
    """
    Open a SQLite database in read-only mode and extract schema.
    """
    try:
        # Use read-only URI connection
        conn = sqlite3.connect(f'file:{file_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = [row[0] for row in cursor.fetchall()]
        
        tables = {}
        for table_name in table_names:
            table_info = _get_sqlite_table_info(cursor, table_name)
            tables[table_name] = table_info
        
        conn.close()
        
        meta = {
            'type': 'sqlite',
            'tables': tables,
            'table_names': table_names,
            'total_tables': len(table_names),
            'status': 'processed'
        }
        return meta
    except Exception as e:
        logger.error(f"SQLite processing error: {e}")
        return {'type': 'sqlite', 'status': 'error', 'error': str(e)}


def _get_sqlite_table_info(cursor, table_name: str) -> dict:
    """Get detailed info about a SQLite table."""
    # Column info
    cursor.execute(f"PRAGMA table_info('{table_name}')")
    columns_raw = cursor.fetchall()
    columns = []
    pks = []
    
    for col in columns_raw:
        col_id, col_name, col_type, not_null, default_val, is_pk = col
        col_info = {
            'name': col_name,
            'type': col_type or 'TEXT',
            'not_null': bool(not_null),
            'default': default_val,
            'is_pk': bool(is_pk)
        }
        columns.append(col_info)
        if is_pk:
            pks.append(col_name)
    
    # Foreign keys
    cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
    fk_raw = cursor.fetchall()
    foreign_keys = []
    for fk in fk_raw:
        foreign_keys.append({
            'column': fk[3],
            'references_table': fk[2],
            'references_column': fk[4]
        })
    
    # Row count
    try:
        cursor.execute(f"SELECT COUNT(*) FROM '{table_name}'")
        row_count = cursor.fetchone()[0]
    except Exception:
        row_count = 0
    
    return {
        'columns': columns,
        'primary_keys': pks,
        'foreign_keys': foreign_keys,
        'row_count': row_count
    }


def get_dataframe_from_file(file_path: str, file_type: str) -> pd.DataFrame:
    """
    Load a file into a pandas DataFrame for analysis and chart generation.
    Used by chart_generator.py and data_analyzer.py.
    """
    try:
        if file_type == 'csv':
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    return pd.read_csv(file_path, encoding=encoding)
                except UnicodeDecodeError:
                    continue
        elif file_type in ('xlsx', 'xls'):
            return pd.read_excel(file_path)
        elif file_type == 'json':
            data = pd.read_json(file_path)
            if isinstance(data, pd.DataFrame):
                return data
        return None
    except Exception as e:
        logger.error(f"Error loading DataFrame from {file_path}: {e}")
        return None
