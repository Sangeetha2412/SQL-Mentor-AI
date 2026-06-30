"""
ingest_docs.py - Global SQL Knowledge Base Ingestion Script
Run this once to populate ChromaDB with SQL documentation.
Usage: python ingest_docs.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from rag_pipeline import ingest_global_sql_docs

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("🚀 Starting SQL documentation ingestion...")
        count = ingest_global_sql_docs()
        print(f"✅ Ingested {count} chunks into ChromaDB global knowledge base.")
        print("You can now start the app with: python app.py")
