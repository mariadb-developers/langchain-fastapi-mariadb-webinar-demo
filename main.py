import os
from contextlib import asynccontextmanager
from urllib.parse import quote

import mariadb
from fastapi import FastAPI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_mariadb import MariaDBStore
from mariadb.connectionpool import ConnectionPool

# MariaDB connection details
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "demo")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))

# Embedding model details
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_LENGTH = 3072
EMBEDDING_TIMEOUT_SECS = int(os.getenv("EMBED_TIMEOUT_SECS", "30"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "100"))
COLLECTION_NAME = "product_descriptions"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Google GenAI embedder
    app.state.embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        task_type="SEMANTIC_SIMILARITY",
        request_options={"timeout": EMBEDDING_TIMEOUT_SECS},
    )

    # MariaDB LangChain vector store
    app.state.vector_store = MariaDBStore(
        embeddings=app.state.embeddings,
        datasource=f"mariadb+mariadbconnector://{DB_USER}:{quote(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}?ssl=true",
        embedding_length=EMBEDDING_LENGTH,
        collection_name=COLLECTION_NAME,
        collection_metadata={
            "embedder": EMBEDDING_MODEL,
            "dimensions": EMBEDDING_LENGTH,
        },
    )

    # MariaDB connection pool
    app.state.connection_pool = ConnectionPool(
        pool_name="mariadb_pool",
        pool_size=DB_POOL_SIZE,
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        ssl=True,
    )

    try:
        yield
    finally:
        app.state.connection_pool.close()


# Fast API object
app = FastAPI(lifespan=lifespan)


# /ingest-products endpoint
@app.post("/ingest-products")
def ingest_products():
    connection_pool: ConnectionPool = app.state.connection_pool
    vector_store: MariaDBStore = app.state.vector_store

    with connection_pool.get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.id, p.name, p.description, p.category
            FROM products p
                LEFT JOIN langchain_collection c ON c.label = ?
                LEFT JOIN langchain_embedding e ON e.collection_id = c.id
                AND JSON_VALUE(e.metadata, '$.id') = p.id
            WHERE e.id IS NULL
                AND p.description IS NOT NULL
                AND TRIM(p.description) <> '';
            """,
            (COLLECTION_NAME,),
        )
        rows = cursor.fetchall()
        vector_store.add_texts(
            texts=[description for id, name, description, category in rows],
            metadatas=[
                {"id": id, "name": name, "category": category}
                for id, name, description, category in rows
            ],
        )

    return {"status": "Ingestion completed"}


# /search-products endpoint
@app.get("/search-products")
def search_products(search_query: str, category: str, k: int = 10):
    vector_store: MariaDBStore = app.state.vector_store
    documents = vector_store.similarity_search(search_query, k, {"category": category})
    results = [
        {
            "id": doc.metadata.get("id"),
            "name": doc.metadata.get("name"),
            "description": doc.page_content,
        }
        for doc in documents
    ]
    return {"results": results}
