import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.security import APIKeyHeader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_mariadb import MariaDBStore
from mariadb.connectionpool import ConnectionPool

# MariaDB connection details
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "demo")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))

# Embedding model details
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_LENGTH = int(os.getenv("EMBEDDING_LENGTH", 3072))
EMBEDDING_TIMEOUT_SECS = int(os.getenv("EMBED_TIMEOUT_SECS", 30))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", 100))
COLLECTION_NAME = "products.description"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(levelname)s:     %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# API security
DEMO_API_KEY = os.getenv("DEMO_API_KEY", "demo-key-123")
api_key_header = APIKeyHeader(name="X-API-Key")


# API key verification
def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != DEMO_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# Lifespan event
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


def run_product_ingestion(connection_pool: ConnectionPool, vector_store: MariaDBStore):
    with connection_pool.get_connection() as connection, connection.cursor() as cursor:
        # Add created_at column if it doesn't exist
        cursor.execute(
            """
            ALTER TABLE langchain_embedding
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)

        # Delete embeddings for products that no longer exist (orphaned embeddings)
        cursor.execute(
            """
            DELETE e FROM langchain_embedding e
            JOIN langchain_collection c ON c.id = e.collection_id
            LEFT JOIN products p ON p.id = JSON_VALUE(e.metadata, '$.id')
            WHERE c.label = ?
                AND p.id IS NULL;
            """,
            (COLLECTION_NAME,),
        )
        orphaned_count = cursor.rowcount

        # Delete embeddings for products that were updated (outdated embeddings)
        cursor.execute(
            """
            DELETE e FROM langchain_embedding e
            JOIN langchain_collection c ON c.id = e.collection_id
            JOIN products p ON p.id = JSON_VALUE(e.metadata, '$.id')
            WHERE c.label = ?
                AND p.updated_at > e.created_at
                AND p.description IS NOT NULL
                AND TRIM(p.description) <> '';
            """,
            (COLLECTION_NAME,),
        )
        outdated_count = cursor.rowcount

        cursor.execute("COMMIT;")
        log.info(
            f"Deleted {orphaned_count} orphaned embeddings and {outdated_count} outdated embeddings"
        )

        # process products that either don't have embeddings
        total_ingested = 0
        has_more_products = True

        while has_more_products:
            # Fetch a batch of products that need embeddings
            cursor.execute(
                """
                SELECT p.id, p.name, p.description, p.category
                FROM products p
                    LEFT JOIN langchain_collection c ON c.label = ?
                    LEFT JOIN langchain_embedding e ON e.collection_id = c.id
                    AND JSON_VALUE(e.metadata, '$.id') = p.id
                WHERE e.id IS NULL
                    AND p.description IS NOT NULL
                    AND TRIM(p.description) <> ''
                ORDER BY p.id
                LIMIT ? OFFSET ?;
                """,
                (COLLECTION_NAME, EMBEDDING_BATCH_SIZE, total_ingested),
            )
            batch_rows = cursor.fetchall()

            has_more_products = bool(batch_rows)

            # Process this batch if we have any products
            if has_more_products:
                vector_store.add_texts(
                    texts=[description for _, _, description, _ in batch_rows],
                    metadatas=[
                        {"id": id, "name": name, "category": category}
                        for id, name, _, category in batch_rows
                    ],
                )
                total_ingested += len(batch_rows)
                log.info(f"Ingested batch of {len(batch_rows)} products")

    log.info(f"Total products ingested: {total_ingested}")


# /ingest-products endpoint
@app.post("/ingest-products")
def ingest_products(
    background_tasks: BackgroundTasks, _: str = Depends(verify_api_key)
):
    connection_pool: ConnectionPool = app.state.connection_pool
    vector_store: MariaDBStore = app.state.vector_store
    background_tasks.add_task(run_product_ingestion, connection_pool, vector_store)

    return {
        "status": "Ingestion started",
        "message": "Product ingestion is running in the background",
    }


# /search-products endpoint
@app.get("/search-products")
def search_products(
    search_query: str, category: str, k: int = 10, _: str = Depends(verify_api_key)
):
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


def main():
    import uvicorn

    log.info("Starting FastAPI backend server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, log_level="info")


if __name__ in {"__main__", "__mp_main__"}:
    main()
