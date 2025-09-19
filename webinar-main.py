import mariadb
from fastapi import FastAPI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_mariadb import MariaDBStore

# MariaDB database connection details
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "password"
DB_DATABASE = "demo"

# MariaDB connection
connection = mariadb.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_DATABASE,
    ssl=True,
)

# MariaDB vector store
vector_store = MariaDBStore(
    embeddings=GoogleGenerativeAIEmbeddings(model="gemini-embedding-001"),
    embedding_length=3072,
    datasource=f"mariadb+mariadbconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}?ssl=true",
)


# FastAPI app
app = FastAPI()


# text search endpoint
@app.get("/products/text-search")
def text_search(query: str):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT name FROM products ORDER BY MATCH(name) AGAINST(?) LIMIT 10;", (query,)
    )
    return [name for (name,) in cursor]


# product ingestion endpoint
@app.post("/products/ingest")
def ingest_products():
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM products;")
    vector_store.add_texts([name for (name,) in cursor])
    return "Products ingested successfully"


# semantic search endpoint
@app.get("/products/semantic-search")
def search_products(query: str):
    results = vector_store.similarity_search(query, k=10)
    return [doc.page_content for doc in results]
