"""
data_analyzer.py - Data Analysis Utilities
Provides analysis helpers for the data explorer and chat responses.
"""

import json
import logging
import pandas as pd
from file_processor import get_dataframe_from_file

logger = logging.getLogger(__name__)


def get_file_analysis_context(file_path: str, file_type: str, filename: str) -> str:
    """
    Build a text summary of a file suitable for including in AI prompts.
    """
    try:
        if file_type in ('csv', 'xlsx', 'xls', 'json'):
            df = get_dataframe_from_file(file_path, file_type)
            if df is not None:
                return _dataframe_summary(df, filename)
        return f"File: {filename} (type: {file_type})"
    except Exception as e:
        logger.error(f"Analysis context error: {e}")
        return f"File: {filename}"


def _dataframe_summary(df: pd.DataFrame, filename: str) -> str:
    """Generate a text summary of a DataFrame for AI context."""
    lines = [f"Dataset: {filename}",
             f"Shape: {df.shape[0]} rows × {df.shape[1]} columns",
             f"Columns: {', '.join(df.columns.tolist())}",
             f"Missing values: {int(df.isnull().sum().sum())}",
             f"Duplicate rows: {int(df.duplicated().sum())}",
             ""]

    lines.append("Column types:")
    for col in df.columns:
        dtype = str(df[col].dtype)
        null_pct = round(df[col].isnull().mean() * 100, 1)
        lines.append(f"  - {col}: {dtype} ({null_pct}% null)")

    lines.append("")
    lines.append("Sample data (first 3 rows):")
    lines.append(df.head(3).fillna('').to_string())

    return "\n".join(lines)


def get_paginated_data(file_path: str, file_type: str, page: int = 1,
                       per_page: int = 50, search: str = None,
                       sort_col: str = None, sort_dir: str = 'asc') -> dict:
    """
    Return paginated, searchable, sortable data for the data explorer.
    """
    df = get_dataframe_from_file(file_path, file_type)
    if df is None:
        return {'error': 'Could not load file', 'rows': [], 'total': 0}

    total_rows = len(df)

    # Search across all string columns
    if search and search.strip():
        mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        df = df[mask]

    # Sort
    if sort_col and sort_col in df.columns:
        ascending = sort_dir != 'desc'
        df = df.sort_values(by=sort_col, ascending=ascending)

    filtered_total = len(df)
    total_pages = max(1, (filtered_total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    page_df = df.iloc[start:start + per_page].fillna('').astype(str)

    return {
        'rows': page_df.to_dict(orient='records'),
        'columns': list(df.columns),
        'total_rows': total_rows,
        'filtered_total': filtered_total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    }
