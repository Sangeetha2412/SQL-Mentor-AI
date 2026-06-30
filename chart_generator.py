"""
chart_generator.py - Chart Configuration Generator
Generates Chart.js configurations from uploaded data files.
"""

import json
import logging
import pandas as pd
from file_processor import get_dataframe_from_file

logger = logging.getLogger(__name__)

CHART_COLORS = [
    'rgba(124, 58, 237, 0.7)', 'rgba(167, 139, 250, 0.7)', 'rgba(196, 181, 253, 0.7)',
    'rgba(219, 234, 254, 0.7)', 'rgba(252, 231, 243, 0.7)', 'rgba(34, 197, 94, 0.7)',
    'rgba(245, 158, 11, 0.7)', 'rgba(239, 68, 68, 0.7)', 'rgba(59, 130, 246, 0.7)',
    'rgba(16, 185, 129, 0.7)'
]

BORDER_COLORS = [c.replace('0.7', '1') for c in CHART_COLORS]


def generate_chart(file_path: str, file_type: str, chart_type: str,
                   x_column: str, y_column: str, aggregation: str = 'count',
                   group_by: str = None) -> dict:
    """
    Generate a Chart.js config from a file.
    Returns chart_config dict or error dict.
    """
    df = get_dataframe_from_file(file_path, file_type)
    if df is None:
        return {'error': 'Could not load file as table data'}

    if x_column not in df.columns:
        return {'error': f'Column "{x_column}" not found'}

    try:
        # Aggregate data
        if aggregation == 'count':
            grouped = df.groupby(x_column).size().reset_index(name='value')
        elif y_column and y_column in df.columns:
            agg_map = {'sum': 'sum', 'average': 'mean', 'min': 'min', 'max': 'max'}
            agg_fn = agg_map.get(aggregation, 'sum')
            grouped = df.groupby(x_column)[y_column].agg(agg_fn).reset_index(name='value')
        else:
            grouped = df.groupby(x_column).size().reset_index(name='value')

        grouped = grouped.dropna().head(20)
        labels = [str(v) for v in grouped.iloc[:, 0].tolist()]
        values = [round(float(v), 4) for v in grouped['value'].tolist()]

        chart_config = _build_chart_config(chart_type, labels, values, x_column, y_column or 'Count', aggregation)
        insight = _generate_insight(chart_type, labels, values, x_column, aggregation)

        return {'success': True, 'chart_config': chart_config, 'insight': insight,
                'labels': labels, 'values': values}

    except Exception as e:
        logger.error(f"Chart generation error: {e}")
        return {'error': str(e)}


def _build_chart_config(chart_type: str, labels: list, values: list,
                        x_label: str, y_label: str, aggregation: str) -> dict:
    """Build a Chart.js configuration object."""
    n = len(labels)
    colors = (CHART_COLORS * ((n // len(CHART_COLORS)) + 1))[:n]
    borders = (BORDER_COLORS * ((n // len(BORDER_COLORS)) + 1))[:n]

    base_dataset = {
        'label': f'{aggregation.capitalize()} of {y_label}',
        'data': values,
        'backgroundColor': colors if chart_type in ('pie', 'doughnut') else colors[0],
        'borderColor': borders if chart_type in ('pie', 'doughnut') else borders[0],
        'borderWidth': 2,
        'borderRadius': 6,
        'tension': 0.4
    }

    type_map = {'bar': 'bar', 'horizontal_bar': 'bar', 'line': 'line',
                'pie': 'pie', 'doughnut': 'doughnut', 'scatter': 'scatter',
                'area': 'line', 'histogram': 'bar'}
    chart_js_type = type_map.get(chart_type, 'bar')

    if chart_type == 'area':
        base_dataset['fill'] = True
        base_dataset['backgroundColor'] = 'rgba(124, 58, 237, 0.15)'

    options = {
        'responsive': True,
        'maintainAspectRatio': False,
        'plugins': {
            'legend': {'position': 'top', 'labels': {'font': {'family': 'Inter'}}},
            'title': {'display': True, 'text': f'{y_label} by {x_label}',
                      'font': {'size': 16, 'family': 'Inter'}}
        }
    }

    if chart_type == 'horizontal_bar':
        options['indexAxis'] = 'y'

    if chart_js_type not in ('pie', 'doughnut'):
        options['scales'] = {
            'x': {'grid': {'color': 'rgba(0,0,0,0.05)'},
                  'ticks': {'font': {'family': 'Inter'}}},
            'y': {'grid': {'color': 'rgba(0,0,0,0.05)'},
                  'ticks': {'font': {'family': 'Inter'}}}
        }

    return {'type': chart_js_type, 'data': {'labels': labels, 'datasets': [base_dataset]}, 'options': options}


def _generate_insight(chart_type: str, labels: list, values: list,
                      x_column: str, aggregation: str) -> str:
    """Generate a brief AI-style insight about the chart."""
    if not values:
        return "No data available for insight."
    max_val = max(values)
    min_val = min(values)
    max_label = labels[values.index(max_val)]
    min_label = labels[values.index(min_val)]
    total = sum(values)
    avg = total / len(values) if values else 0

    return (f"**Chart Insight:** The highest value is **{max_label}** ({max_val:,.2f}), "
            f"and the lowest is **{min_label}** ({min_val:,.2f}). "
            f"Average across all categories: **{avg:,.2f}**. "
            f"Total: **{total:,.2f}** across {len(labels)} categories.")
