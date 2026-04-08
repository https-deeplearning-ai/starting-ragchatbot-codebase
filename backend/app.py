import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
import pathlib
import shutil
# Add the backend directory to Python path
backend_path = pathlib.Path(__file__).parent
sys.path.append(str(backend_path))

# Use relative imports
from config import config
from rag_system import RAGSystem
from language_detector import detect_language

# Initialize FastAPI app
app = FastAPI(title="Course Materials RAG System", root_path="")

# Add trusted host middleware for proxy
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Initialize RAG system
rag_system = RAGSystem(config)

# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None
    language: Optional[str] = None  # 'en' or 'zh' - user's language preference

class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[str]
    session_id: str

class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]

class ClearSessionRequest(BaseModel):
    """Request model for clearing a session"""
    session_id: str

# API Endpoints

@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()

        # Determine language: user preference > session language > detected language
        if request.language:
            # User explicitly selected a language
            language = request.language
            rag_system.session_manager.set_session_language(session_id, language)
        else:
            # Check session language
            session_language = rag_system.session_manager.get_session_language(session_id)
            if session_language is None:
                # First query in session - detect language from query
                detected_language = detect_language(request.query)
                rag_system.session_manager.set_session_language(session_id, detected_language)
                language = detected_language
            else:
                # Use existing session language for consistency
                language = session_language

        # Process query using RAG system with language parameter
        answer, sources = rag_system.query(request.query, session_id, language)

        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
    """Get course analytics and statistics"""
    try:
        analytics = rag_system.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/clear")
async def clear_session(request: ClearSessionRequest):
    """Clear a conversation session"""
    try:
        rag_system.session_manager.clear_session(request.session_id)
        return {"status": "success", "message": f"Session {request.session_id} cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
async def test_route():
    return {"status": "success", "message": "Test route working"}

@app.post("/api/upload-course", include_in_schema=True)
async def upload_course(file: UploadFile = File(...)):
    print(f"Received file upload request: {file.filename}")
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Only .txt files are allowed")

    docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    os.makedirs(docs_path, exist_ok=True)
    print(f"Docs path: {docs_path}")

    file_path = os.path.join(docs_path, file.filename)
    print(f"Saving file to: {file_path}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        print("Processing course document...")
        course_title = rag_system.add_course_document(file_path)
        print(f"Successfully processed course: {course_title}")
        return {"status": "success", "course_title": course_title}
    except Exception as e:
        print(f"Error processing file: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    if os.path.exists(docs_path):
        print("Loading initial documents...")
        try:
            courses, chunks = rag_system.add_course_folder(docs_path)
            print(f"Successfully loaded {courses} courses with {chunks} chunks")
        except Exception as e:
            print(f"Error loading documents: {e}")
    else:
        print(f"Warning: docs directory not found at {docs_path}")

# Custom static file handler with no-cache headers for development
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
    
    
# Serve static files for the frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")