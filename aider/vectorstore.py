import yaml
import psycopg2
from psycopg2.extras import Json
import uuid
from typing import Dict, List, Any

class VectorStore:
    def __init__(self, config_file: str):
        self.config = self.load_config(config_file)
        self.connection = None

    def load_config(self, config_file: str) -> Dict[str, Any]:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def connect(self) -> bool:
        try:
            self.connection = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database']
            )
            return True
        except psycopg2.Error as e:
            print(f"Error connecting to database: {e}")
            return False

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def is_connected(self) -> bool:
        return self.connection is not None and not self.connection.closed

    def add_vector(self, chunk: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        if not self.is_connected():
            print("Not connected to the database. Call connect() first.")
            return False

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO {self.config['schema_name']}.{self.config['table_name']} (id, chunks, embedding, metadata) VALUES (%s, %s, %s::vector, %s)",
                    (uuid.uuid4(), chunk, embedding, Json(metadata))
                )
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Error adding vector: {e}")
            self.connection.rollback()
            return False

    def search_vectors(self, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        if not self.is_connected():
            print("Not connected to the database. Call connect() first.")
            return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT id, chunks, metadata, embedding <-> %s::vector AS distance FROM {self.config['schema_name']}.{self.config['table_name']} ORDER BY distance LIMIT %s",
                    (query_embedding, limit)
                )
                results = cursor.fetchall()
            return [
                {
                    'id': str(row[0]),
                    'chunk': row[1],
                    'metadata': row[2],
                    'distance': row[3]
                }
                for row in results
            ]
        except psycopg2.Error as e:
            print(f"Error searching vectors: {e}")
            return []

    def create_schema_and_table_if_not_exists(self) -> bool:
        if not self.is_connected():
            print("Not connected to the database. Call connect() first.")
            return False

        try:
            with self.connection.cursor() as cursor:
                # Create schema if not exists
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.config['schema_name']}")
                
                # Create extension if not exists
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                
                # Create table if not exists
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config['schema_name']}.{self.config['table_name']} (
                        id uuid PRIMARY KEY,
                        chunks TEXT,
                        embedding vector({self.config['vector_dimension']}),
                        metadata JSONB
                    )
                """)
                
                # Create index if not exists
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.config['table_name']}_embedding 
                    ON {self.config['schema_name']}.{self.config['table_name']} 
                    USING hnsw (embedding vector_cosine_ops) 
                    WITH (ef_construction=256)
                """)
            
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Error creating schema and table: {e}")
            self.connection.rollback()
            return False
