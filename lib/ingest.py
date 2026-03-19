import os

# Silence IDE warnings when dependencies are not installed locally.
# (They are installed inside the Docker build for this lab.)
# basedpyright: reportMissingImports=false
from sqlalchemy import create_engine, text


host = os.getenv("POSTGRES_HOST","localhost")
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
db = os.getenv("POSTGRES_DB")
name = os.getenv("YOUR_NAME", "Anne O'Nyme")

print(f"Host: {host}")
print(f"User: {user}")
print(f"Password: {password}")
print(f"Database: {db}")
print(f"Name: {name}")

sql_ddl = """
CREATE TABLE IF NOT EXISTS bootcamp_test (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL
);
"""

sql_insert = """
INSERT INTO bootcamp_test (name)
VALUES (:name);
"""

engine_url = f"postgresql+psycopg2://{user}:{password}@{host}:5432/{db}"
engine = create_engine(engine_url, future=True)

with engine.begin() as conn:
    conn.execute(text(sql_ddl))
    conn.execute(text(sql_insert), {"name": name})

print("Data ingested successfully into the database")

print(f"Engine URL: {engine_url}")