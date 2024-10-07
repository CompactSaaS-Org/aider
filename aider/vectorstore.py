import json
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import Json
import numpy as np

class VectorStore:
    def __init__(self, config_file):
        self.config = self.load_config(config_file)
        self.connection = None

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            return json.load(f)

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=self.config['hostname'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database']
            )
            return True
        except psycopg2.Error as e:
            print(f"Error connecting to database: {e}")
            return False

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def is_connected(self):
        return self.connection is not None and not self.connection.closed

    def add_vector(self, chunk, embedding, metadata):
        if not self.is_connected():
            return False

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO {self.config['table_name']} (chunks, embedding, metadata) VALUES (%s, %s, %s)",
                    (chunk, embedding, Json(metadata))
                )
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Error adding vector: {e}")
            return False

    def search_vectors(self, query_embedding, limit=5):
        if not self.is_connected():
            return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT id, chunks, metadata, embedding <-> %s AS distance FROM {self.config['table_name']} ORDER BY distance LIMIT %s",
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
