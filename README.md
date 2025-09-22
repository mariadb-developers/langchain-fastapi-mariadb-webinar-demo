# MariaDB + LangChain + FastAPI + NiceGUI demo

![Demo Screenshot](https://repository-images.githubusercontent.com/1052128512/6db456c6-83b3-46de-893a-5ed7fcaaed14)

This example application shows how to use MariaDB, LangChain, FastAPI, and NiceGUI to implement the
search functionality for an online store. It uses semantic search storing vectors created by
Google Generative AI in [MariaDB](https://mariadb.com/).

**Note:** If you are looking for the demo implemented during the webinar [Beyond Keywords: AI Vector Search with LangChain and MariaDB Cloud](https://go.mariadb.com/25Q3-WBN-GLBL-OSSG-2025-09-24-AIVectorsearch_Registration-LP.html), see the [webinar-main.py](webinar-main.py) file.

## Prerequisites

You'll need:

- A [MariaDB](https://mariadb.com/downloads/) server up and running (or spin up a free serverless instance in seconds using [MariaDB Cloud](https://mariadb.com/products/cloud/))
- Python 3.11 or later
- pip
- A SQL client compatible with MariaDB (for example, DBeaver, the `mariadb` command-line tool, or an extension for your IDE)

## Preparing the database

Connect to your MariaDB database and create the following table:

```sql
CREATE OR REPLACE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FULLTEXT(name),
    FULLTEXT(description)
);
```

Download [this CSV file](https://raw.githubusercontent.com/mariadb-developers/vector-search-workshop/refs/heads/main/products.csv).

Load the data from that CSV file into the table that you previously created (remember to use the absolute path to your CSV file):

```sql
LOAD DATA LOCAL INFILE '/path/to/products.csv'
INTO TABLE products
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(@dummy_id, name, category, price, description);
```

## Configuring the example application

Download or clone this repository and move to the corresponding directory:

```shell
git clone https://github.com/mariadb-developers/langchain-fastapi-mariadb-webinar-demo.git
cd langchain-fastapi-mariadb-webinar-demo
```

Define the OS environment variables using the values corresponding to you MariaDB database connection and Google Generative AI API key. For example, on Linux:

```
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=password
export DB_NAME=demo
export GOOGLE_API_KEY=key1234567
```

Alternatively, modify the default values for this variables in the [backend.py](backend.py) file.

## Installing the required packages

Create and activate a new virtual environment:

```shell
python3 -m venv venv/
source venv/bin/activate
```

Install the required packages:

```shell
pip install -r requirements.txt
```

## Running the backend

Run the FastAPI backend:

```shell
python backend.py
```

## Calculate and store vector embeddings

Go to http://localhost:8000/docs, authorize (use this API key: `demo-key-123`), and invoke the POST `/ingest-products` endpoint
to calculate and store the vector embeddings. Check the logs in the terminal to confirm 500 products are ingested.

## Running the frontend

**Important!** Run the POST `/ingest-products` endpoint before running using the frontend!

Run the NiceGUI frontend in a separate terminal:

```shell
cd langchain-fastapi-mariadb-webinar-demo
source venv/bin/activate
python frontend.py
```

This should open your default browser pointing to http://127.0.0.1:8080/.
