import json
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import Json
import numpy as np
from typing import Dict, List, Any

class VectorStore:
    def __init__(self, config_file: str):
        self.config = self.load_config(config_file)
        self.connection = None

    def load_config(self, config_file: str) -> Dict[str, Any]:
        with open(config_file, 'r') as f:
            return json.load(f)

    def connect(self) -> bool:
        try:
            self.connection = psycopg2.connect(
                host=self.config['hostname'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database']
            )
            # Enable pgvector extension if not already enabled
            with self.connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self.connection.commit()
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
                    f"INSERT INTO {self.config['table_name']} (chunks, embedding, metadata) VALUES (%s, %s::vector, %s)",
                    (chunk, embedding, Json(metadata))
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
                    f"SELECT id, chunks, metadata, embedding <-> %s::vector AS distance FROM {self.config['table_name']} ORDER BY distance LIMIT %s",
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

    def create_table_if_not_exists(self) -> bool:
        if not self.is_connected():
            print("Not connected to the database. Call connect() first.")
            return False

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config['table_name']} (
                        id SERIAL PRIMARY KEY,
                        chunks TEXT,
                        embedding vector({self.config.get('vector_dimension', 1536)}),
                        metadata JSONB
                    )
                """)
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.config['table_name']}_embedding ON {self.config['table_name']} USING ivfflat (embedding vector_cosine_ops)")
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Error creating table: {e}")
            self.connection.rollback()
            return False
