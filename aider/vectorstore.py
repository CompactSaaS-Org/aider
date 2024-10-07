import yaml
import psycopg2
from psycopg2.extras import Json
import uuid
from typing import Dict, List, Any
import boto3
import json

class VectorStore:
    def __init__(self, config_file: str):
        self.config = self.load_config(config_file)
        self.connection = None
        self.bedrock_runtime = None

    def load_config(self, config_file: str) -> Dict[str, Any]:
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            if not isinstance(config, dict):
                raise ValueError("Config file does not contain a valid YAML dictionary")
            required_keys = ['host', 'port', 'user', 'password', 'database', 'schema_name', 'table_name', 'vector_dimension', 'aws_region']
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                raise ValueError(f"Missing required keys in config file: {', '.join(missing_keys)}")
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML in config file: {e}")
        except IOError as e:
            raise ValueError(f"Error reading config file '{config_file}': {e}")

    def connect(self, verbose=False) -> bool:
        try:
            if verbose:
                print(f"Attempting to connect to vector database at {self.config['host']}:{self.config['port']}...")
            self.connection = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database']
            )
            if verbose:
                print(f"Successfully connected to vector database {self.config['database']}.")
            return True
        except psycopg2.Error as e:
            if verbose:
                print(f"Error connecting to vector database: {e}")
                print(f"Connection details: host={self.config['host']}, port={self.config['port']}, user={self.config['user']}, database={self.config['database']}")
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
                    (str(uuid.uuid4()), chunk, embedding, Json(metadata))
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

    def upload_document(self, document_text: str, metadata: Dict[str, Any]) -> bool:
        if not self.bedrock_runtime:
            raise ValueError("Bedrock client not initialized. Call connect_to_bedrock() first.")

        # For simplicity, we're treating the entire document as one chunk
        # In a real-world scenario, you'd want to split the document into smaller chunks
        embedding = self.generate_embedding(document_text)
        return self.add_vector(document_text, embedding, metadata)

    def get_connection_status(self) -> str:
        if self.is_connected():
            return "Connected to vector store"
        else:
            return "Not connected to vector store"

    def connect_to_bedrock(self, aws_profile: str = None):
        session = boto3.Session(profile_name=aws_profile) if aws_profile else boto3.Session()
        self.bedrock_runtime = session.client(
            service_name='bedrock-runtime',
            region_name=self.config['aws_region']
        )

    def generate_embedding(self, text: str) -> List[float]:
        if not self.bedrock_runtime:
            raise ValueError("Bedrock client not initialized. Call connect_to_bedrock() first.")

        body = json.dumps({"inputText": text})
        response = self.bedrock_runtime.invoke_model(
            body=body,
            modelId='amazon.titan-embed-text-v1',
            accept='application/json',
            contentType='application/json'
        )
        response_body = json.loads(response['body'].read())
        embedding = response_body.get('embedding')
        return embedding

    def create_schema_and_table_if_not_exists(self, verbose=False) -> bool:
        if not self.is_connected():
            if verbose:
                print("Not connected to the vector database. Call connect() first.")
            return False

        try:
            with self.connection.cursor() as cursor:
                if verbose:
                    print("Setting up vector database schema and table...")
                
                # Create schema if not exists
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.config['schema_name']}")
                if verbose:
                    print(f"Schema '{self.config['schema_name']}' created or already exists.")
                
                # Create extension if not exists
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                if verbose:
                    print("Vector extension created or already exists.")
                
                # Create table if not exists
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config['schema_name']}.{self.config['table_name']} (
                        id uuid PRIMARY KEY,
                        chunks TEXT,
                        embedding vector({self.config['vector_dimension']}),
                        metadata JSONB
                    )
                """)
                if verbose:
                    print(f"Table '{self.config['table_name']}' created or already exists.")
                
                # Create index if not exists
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.config['table_name']}_embedding 
                    ON {self.config['schema_name']}.{self.config['table_name']} 
                    USING hnsw (embedding vector_cosine_ops) 
                    WITH (ef_construction=256)
                """)
                if verbose:
                    print(f"Index on '{self.config['table_name']}' created or already exists.")
            
            self.connection.commit()
            if verbose:
                print("Vector database setup completed successfully.")
            return True
        except psycopg2.Error as e:
            if verbose:
                print(f"Error creating schema and table: {e}")
            self.connection.rollback()
            return False
