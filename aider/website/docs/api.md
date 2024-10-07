---
title: API
nav_order: 8
---

# Aider API

Aider now provides an API server that allows programmatic access to its functionality. This enables integration with other tools and workflows.

## Starting the API Server

To start Aider in API server mode, use the following command:

```bash
aider --api
```

By default, the API server will run on `localhost:8080`. You can customize the host and port using the `--host` and `--port` options:

```bash
aider --api --host 0.0.0.0 --port 5000
```

## API Endpoints

The Aider API provides the following endpoints:

### POST /chat

Send a chat message to Aider and receive a response.

**Request Body:**
```json
{
  "message": "Your chat message here"
}
```

**Response:**
```json
{
  "response": "Aider's response to your message"
}
```

### POST /files

Add or update files in the current working context.

**Request Body:**
```json
{
  "files": [
    {
      "name": "example.py",
      "content": "print('Hello, World!')"
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Files updated successfully"
}
```

### GET /files

Retrieve the current files in the working context.

**Response:**
```json
{
  "files": [
    {
      "name": "example.py",
      "content": "print('Hello, World!')"
    }
  ]
}
```

### POST /run

Execute a command in the current working context.

**Request Body:**
```json
{
  "command": "git status"
}
```

**Response:**
```json
{
  "output": "Command output here"
}
```

### GET /model

Get information about the currently used AI model.

**Response:**
```json
{
  "model": "gpt-4",
  "provider": "openai"
}
```

### POST /model

Change the AI model being used.

**Request Body:**
```json
{
  "model": "gpt-3.5-turbo",
  "provider": "openai"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Model changed successfully"
}
```

## Using the API

You can interact with the Aider API using any HTTP client. Here's an example using Python's `requests` library:

```python
import requests

API_URL = "http://localhost:8080"

# Send a chat message
response = requests.post(f"{API_URL}/chat", json={"message": "Hello, Aider!"})
print(response.json()["response"])

# Add a file
files = [{"name": "example.py", "content": "print('Hello from API!')"}]
response = requests.post(f"{API_URL}/files", json={"files": files})
print(response.json()["message"])

# Run a command
response = requests.post(f"{API_URL}/run", json={"command": "python example.py"})
print(response.json()["output"])
```

This API allows you to integrate Aider's capabilities into your own applications, scripts, or development workflows.
