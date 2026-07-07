"""
rag_pipeline.py - RAG (Retrieval-Augmented Generation) Pipeline
Handles vector embeddings, ChromaDB storage, and AI response generation.
Uses Groq LLM + sentence-transformers for embeddings.
"""

import os
import json
import logging
from typing import List, Optional
import chromadb
from chromadb.config import Settings
from encryption_utils import get_groq_api_key
from config import Config
import requests

logger = logging.getLogger(__name__)

# Global ChromaDB client and embedding model (loaded once)
_chroma_client = None
_embedding_model = None


def _get_chroma_client():
    """Initialize and return ChromaDB client (singleton pattern)."""
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(Config.CHROMA_DB_PATH, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=Config.CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        logger.info("ChromaDB client initialized")
    return _chroma_client


def _get_embedding_model():
    return None


def get_embeddings(texts: List[str]) -> List[List[float]]:
    raise NotImplementedError("Embeddings are disabled.")


def _get_collection(collection_name: str):
    """Get or create a ChromaDB collection."""
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


def _chunk_text(text, chunk_size=800, overlap=100):

    if not text:
        return []

    step = chunk_size - overlap

    if step <= 0:
        step = chunk_size

    chunks = []

    for start in range(0, len(text), step):
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

    return chunks

def ingest_global_sql_docs():
    """
    Ingest all SQL documentation files from data/sql_docs/ into ChromaDB.
    This builds the global SQL knowledge base.
    """
    collection = _get_collection('sql_global_knowledge')
    docs_path = Config.SQL_DOCS_PATH
    
    if not os.path.exists(docs_path):
        logger.warning(f"SQL docs path does not exist: {docs_path}")
        return 0
    
    ingested = 0
    for filename in os.listdir(docs_path):
        if filename.endswith(('.md', '.txt', '.sql')):
            filepath = os.path.join(docs_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                chunks = _chunk_text(content)
                if not chunks:
                    continue
                
                # Create unique IDs for each chunk
                ids = [f"global_{filename}_{i}" for i in range(len(chunks))]
                embeddings = get_embeddings(chunks)
                metadatas = [{'source': filename, 'type': 'global_sql_doc'} for _ in chunks]
                
                # Upsert (update if exists, insert if not)
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadatas
                )
                ingested += len(chunks)
                logger.info(f"Ingested {len(chunks)} chunks from {filename}")
            
            except Exception as e:
                logger.error(f"Error ingesting {filename}: {e}")
    
    logger.info(f"Total global chunks ingested: {ingested}")
    return ingested


def ingest_user_file(file_id: int, user_id: int, text_content: str, filename: str, file_type: str):
    """
    Ingest a user's file content into their private ChromaDB collection.
    Each user has their own collection to ensure data isolation.
    """
    # Each user gets their own collection
    collection_name = f'user_{user_id}_files'
    collection = _get_collection(collection_name)
    
    if not text_content or not text_content.strip():
     logger.warning(f"Empty content for file {filename}")
     return 0

    print("TEXT LENGTH:", len(text_content))   # <-- ADD THIS

    chunks = _chunk_text(text_content)

    print("TOTAL CHUNKS:", len(chunks))        # <-- ADD THIS

    if not chunks:
        return 0
        
    # Prefix IDs with file_id to allow deletion per file
    ids = [f"file_{file_id}_chunk_{i}" for i in range(len(chunks))]
    embeddings = get_embeddings(chunks)
    metadatas = [
        {
            'file_id': str(file_id),
            'filename': filename,
            'file_type': file_type,
            'user_id': str(user_id)
        }
        for _ in chunks
    ]
    
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )
    
    logger.info(f"Ingested {len(chunks)} chunks for user {user_id}, file {filename}")
    return len(chunks)


def delete_user_file_vectors(file_id: int, user_id: int):
    """Remove all ChromaDB vectors for a specific user file."""
    try:
        collection_name = f'user_{user_id}_files'
        client = _get_chroma_client()
        
        # Check if collection exists
        try:
            collection = client.get_collection(collection_name)
        except Exception:
            return  # Collection doesn't exist, nothing to delete
        
        # Delete all chunks for this file
        results = collection.get(where={'file_id': str(file_id)})
        if results and results['ids']:
            collection.delete(ids=results['ids'])
            logger.info(f"Deleted {len(results['ids'])} vectors for file {file_id}")
    except Exception as e:
        logger.error(f"Error deleting vectors for file {file_id}: {e}")


def retrieve_relevant_chunks(query: str, user_id: int, file_ids: List[int] = None, n_results: int = 5) -> dict:
    """
    Retrieve the most relevant text chunks for a query.
    Searches both global SQL knowledge and user's private files.
    
    Returns dict with global_results and user_results.
    """
    query_embedding = get_embeddings([query])[0]
    
    results = {
        'global_chunks': [],
        'user_chunks': [],
        'sources': []
    }
    
    # Search global SQL knowledge base
    try:
        global_collection = _get_collection('sql_global_knowledge')
        global_results = global_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, 3),
            include=['documents', 'metadatas', 'distances']
        )
        if global_results['documents'] and global_results['documents'][0]:
            for doc, meta, dist in zip(
                global_results['documents'][0],
                global_results['metadatas'][0],
                global_results['distances'][0]
            ):
                if dist < 0.8:  # Only include relevant results
                    results['global_chunks'].append(doc)
                    if meta.get('source') not in results['sources']:
                        results['sources'].append(meta.get('source', 'SQL Knowledge Base'))
    except Exception as e:
        logger.warning(f"Error querying global knowledge: {e}")
    
    # Search user's private files
    try:
        user_collection_name = f'user_{user_id}_files'
        client = _get_chroma_client()
        
        try:
            user_collection = client.get_collection(user_collection_name)
            
            # Build where filter for specific files if provided
            where_filter = None
            if file_ids and len(file_ids) == 1:
                where_filter = {'file_id': str(file_ids[0])}
            elif file_ids and len(file_ids) > 1:
                where_filter = {'file_id': {'$in': [str(fid) for fid in file_ids]}}
            
            user_results = user_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, 5),
                where=where_filter,
                include=['documents', 'metadatas', 'distances']
            )
            
            if user_results['documents'] and user_results['documents'][0]:
                for doc, meta, dist in zip(
                    user_results['documents'][0],
                    user_results['metadatas'][0],
                    user_results['distances'][0]
                ):
                    if dist < 0.85:
                        results['user_chunks'].append(doc)
                        fname = meta.get('filename', 'Uploaded File')
                        if fname not in results['sources']:
                            results['sources'].append(fname)
        except Exception:
            pass  # User has no collection yet
    except Exception as e:
        logger.warning(f"Error querying user knowledge: {e}")
    
    return results


def generate_ai_response(
    user_message: str,
    chat_history: List[dict],
    user_id: int,
    selected_file_ids: List[int] = None,
    file_metadata: dict = None
) -> dict:
    """
    Generate an AI response using RAG + Groq LLM.
    
    Steps:
    1. Retrieve relevant chunks from ChromaDB
    2. Build context-aware prompt
    3. Call Groq API
    4. Return response with sources
    """
    api_key = get_groq_api_key()
    
    if not api_key:
        return {
            'response': "⚠️ **Groq API key is not configured.** Please ask the admin to update the API key in Admin Settings.",
            'sources': [],
            'error': True
        }
    
    # Retrieve relevant chunks
    retrieved = {
    "global_chunks": [],
    "user_chunks": [],
    "sources": []
}
    
    # Build context from retrieved chunks
    context = ""
    
    # Build system prompt
    system_prompt = """You are SQL Mentor AI, an expert SQL tutor and data analyst assistant.

Your capabilities:
- Explain SQL concepts clearly with examples
- Write optimized SQL queries for any database system
- Debug and fix SQL errors
- Analyze uploaded data files (CSV, Excel, JSON, PDF, SQLite)
- Generate chart configurations for data visualization
- Help with database design and normalization

Response guidelines:
- Always format SQL code in ```sql code blocks
- Specify the SQL dialect (MySQL, PostgreSQL, SQLite, SQL Server) when relevant
- Add line-by-line explanations when asked
- Include sample data and expected output when helpful
- Warn about destructive queries (DROP, DELETE, UPDATE)
- For uploaded database files, only generate safe SELECT queries
- If information is not available in your context, say exactly: "I could not find this information in the selected SQL knowledge base or uploaded files."

Format your responses in clear Markdown with proper headings, code blocks, and lists."""

    # Build messages list for Groq
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add context as a system message if we have relevant content
    
    
    # Add recent chat history (last 10 messages to stay within token limits)
    for msg in chat_history[-10:]:
        messages.append({
            "role": msg['role'],
            "content": msg['content']
        })
    
    # Add the current user message
    messages.append({"role": "user", "content": user_message})
    
    # Call Groq API
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': Config.GROQ_MODEL,
            'messages': messages,
            'max_tokens': 2048,
            'temperature': 0.3,
            'stream': False
        }
        
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_message = data['choices'][0]['message']['content']
            return {
                'response': ai_message,
                'sources': retrieved['sources'],
                'error': False
            }
        elif response.status_code == 401:
            return {
                'response': "⚠️ **Groq API key is invalid or expired.** Please ask the admin to update it in Admin API Settings.",
                'sources': [],
                'error': True
            }
        elif response.status_code == 429:
            return {
                'response': "⚠️ **API rate limit reached.** Please wait a moment and try again.",
                'sources': [],
                'error': True
            }
        else:
            logger.error(f"Groq API error {response.status_code}: {response.text}")
            return {
                'response': f"⚠️ **AI service error.** Status: {response.status_code}. Please try again.",
                'sources': [],
                'error': True
            }
    
    except requests.exceptions.Timeout:
        return {
            'response': "⚠️ **Request timed out.** The AI service is taking too long. Please try again.",
            'sources': [],
            'error': True
        }
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        return {
            'response': f"⚠️ **Connection error.** Could not reach AI service: {str(e)}",
            'sources': [],
            'error': True
        }


def get_chroma_stats() -> dict:
    """Get ChromaDB statistics for admin system status page."""
    try:
        client = _get_chroma_client()
        collections = client.list_collections()
        
        total_docs = 0
        collection_details = []
        
        for col in collections:
            count = col.count()
            total_docs += count
            collection_details.append({
                'name': col.name,
                'count': count
            })
        
        return {
            'status': 'connected',
            'total_collections': len(collections),
            'total_documents': total_docs,
            'collections': collection_details
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'total_documents': 0
        }
