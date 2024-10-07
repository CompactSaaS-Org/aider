from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from aider.coders import Coder
from aider.io import InputOutput
from aider.repo import GitRepo
import os

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    files: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
    edits: Optional[List[Dict[str, str]]] = None

class FileRequest(BaseModel):
    path: str
    content: str

class FileResponse(BaseModel):
    path: str
    content: str

class CommandRequest(BaseModel):
    command: str

class CommandResponse(BaseModel):
    output: str

def get_coder():
    io = InputOutput(pretty=False, yes_always=True)
    repo = GitRepo(io, [], None)
    coder = Coder.create(io=io, repo=repo)
    return coder

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, coder: Coder = Depends(get_coder)):
    response = coder.run_stream(request.message)
    edits = [{"file": edit[0], "content": edit[1]} for edit in coder.get_edits()]
    return ChatResponse(response="".join(response), edits=edits)

@app.post("/add_file", response_model=FileResponse)
async def add_file(request: FileRequest, coder: Coder = Depends(get_coder)):
    coder.add_rel_fname(request.path)
    coder.io.write_text(coder.abs_root_path(request.path), request.content)
    return FileResponse(path=request.path, content=request.content)

@app.get("/files", response_model=List[str])
async def list_files(coder: Coder = Depends(get_coder)):
    return coder.get_all_relative_files()

@app.get("/file/{path:path}", response_model=FileResponse)
async def get_file(path: str, coder: Coder = Depends(get_coder)):
    content = coder.io.read_text(coder.abs_root_path(path))
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=path, content=content)

@app.post("/command", response_model=CommandResponse)
async def run_command(request: CommandRequest, coder: Coder = Depends(get_coder)):
    output = coder.commands.run(request.command)
    return CommandResponse(output=output)

@app.get("/model_info")
async def get_model_info(coder: Coder = Depends(get_coder)):
    return coder.main_model.info

@app.post("/set_model")
async def set_model(model_name: str, coder: Coder = Depends(get_coder)):
    try:
        coder.main_model = coder.main_model.__class__(model_name)
        return {"message": f"Model set to {model_name}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
