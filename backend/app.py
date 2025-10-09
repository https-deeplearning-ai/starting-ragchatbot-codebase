import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union, Dict, Any
import os
import time

from config import config
from rag_system import RAGSystem
from logger import get_logger
from error_handlers import (
    RAGSystemError,
    validation_exception_handler,
    http_exception_handler,
    rag_system_exception_handler,
    general_exception_handler,
    log_request_response
)

# Initialize logger
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Course Materials RAG System", root_path="")

# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RAGSystemError, rag_system_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# Request/Response logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()

    # Log incoming request
    logger.info(f"Incoming {request.method} request to {request.url}")

    # Process request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time

    # Log response
    log_request_response(request, response.status_code, process_time)

    return response

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=config.ALLOWED_HOSTS if config.ENVIRONMENT != "development" else ["*"]
)

# Enable CORS with security-conscious settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS if config.ENVIRONMENT != "development" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Type"],
)

# Initialize RAG system
rag_system = RAGSystem(config)

# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str = Field(..., min_length=1, max_length=2000, description="The search query")
    session_id: Optional[str] = Field(None, max_length=100, description="Optional session ID")

    @validator('query')
    def query_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty or contain only whitespace')
        return v.strip()

    @validator('session_id')
    def session_id_must_be_valid(cls, v):
        if v and not v.startswith('session_'):
            raise ValueError('Session ID must start with "session_"')
        return v

class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[Union[str, Dict[str, Any]]]  # Support both string and object sources
    session_id: str

class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]

class ClearSessionRequest(BaseModel):
    """Request model for clearing a session"""
    session_id: str = Field(..., min_length=1, max_length=100, description="Session ID to clear")

    @validator('session_id')
    def session_id_must_be_valid(cls, v):
        if not v.startswith('session_'):
            raise ValueError('Session ID must start with "session_"')
        return v

class ClearSessionResponse(BaseModel):
    """Response model for clearing a session"""
    success: bool
    message: str

class CourseOutlineRequest(BaseModel):
    """Request model for course outline"""
    course_title: str = Field(..., min_length=1, max_length=200, description="Course title to get outline for")

    @validator('course_title')
    def course_title_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Course title cannot be empty or contain only whitespace')
        return v.strip()

class CourseOutlineResponse(BaseModel):
    """Response model for course outline"""
    course_title: str
    course_link: Optional[str]
    lessons: List[Dict[str, Any]]
    total_lessons: int
    formatted_outline: str

class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    version: str
    environment: str
    timestamp: str
    components: Dict[str, Dict[str, Any]]

# API Endpoints

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Comprehensive health check endpoint"""
    from datetime import datetime
    import psutil

    try:
        # Check vector store health
        vector_store_status = {"status": "healthy", "details": {}}
        try:
            course_count = rag_system.vector_store.get_course_count()
            vector_store_status["details"]["course_count"] = course_count
            vector_store_status["details"]["database_path"] = config.CHROMA_PATH
        except Exception as e:
            vector_store_status = {"status": "unhealthy", "error": str(e)}

        # Check AI generator health (basic connectivity test)
        ai_generator_status = {"status": "healthy", "details": {}}
        try:
            # Check if API key is configured
            if not config.ANTHROPIC_API_KEY:
                ai_generator_status = {"status": "unhealthy", "error": "API key not configured"}
            else:
                ai_generator_status["details"]["model"] = config.ANTHROPIC_MODEL
                ai_generator_status["details"]["api_key_configured"] = True
        except Exception as e:
            ai_generator_status = {"status": "unhealthy", "error": str(e)}

        # System metrics
        system_status = {
            "status": "healthy",
            "details": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent
            }
        }

        # Overall status
        all_healthy = all([
            vector_store_status["status"] == "healthy",
            ai_generator_status["status"] == "healthy",
            system_status["status"] == "healthy"
        ])

        overall_status = "healthy" if all_healthy else "degraded"

        return HealthCheckResponse(
            status=overall_status,
            version="1.0.0",
            environment=config.ENVIRONMENT,
            timestamp=datetime.utcnow().isoformat(),
            components={
                "vector_store": vector_store_status,
                "ai_generator": ai_generator_status,
                "system": system_status
            }
        )
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return HealthCheckResponse(
            status="unhealthy",
            version="1.0.0",
            environment=config.ENVIRONMENT,
            timestamp=datetime.utcnow().isoformat(),
            components={"error": {"status": "unhealthy", "error": str(e)}}
        )

@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()
        
        # Process query using RAG system
        answer, sources = rag_system.query(request.query, session_id)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
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
        logger.error(f"Query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clear_session", response_model=ClearSessionResponse)
async def clear_session(request: ClearSessionRequest):
    """Clear a conversation session"""
    try:
        rag_system.session_manager.clear_session(request.session_id)
        return ClearSessionResponse(
            success=True,
            message="Session cleared successfully"
        )
    except Exception as e:
        logger.error(f"Clear session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/course_outline", response_model=CourseOutlineResponse)
async def get_course_outline(request: CourseOutlineRequest):
    """Get course outline directly from vector store (fast)"""
    try:
        # Use the CourseOutlineTool directly for fast access
        result = rag_system.outline_tool.execute(request.course_title)

        # If it's an error message, throw HTTP exception
        if result.startswith("No course found") or result.startswith("No courses available"):
            raise HTTPException(status_code=404, detail=result)

        # Get the raw course metadata for structured response
        all_courses = rag_system.vector_store.get_all_courses_metadata()
        matching_course = None
        course_title_lower = request.course_title.lower()

        # Find matching course
        for course in all_courses:
            if course.get('title', '').lower() == course_title_lower or course_title_lower in course.get('title', '').lower():
                matching_course = course
                break

        if not matching_course:
            raise HTTPException(status_code=404, detail=f"Course not found: {request.course_title}")

        return CourseOutlineResponse(
            course_title=matching_course.get('title', 'Unknown'),
            course_link=matching_course.get('course_link'),
            lessons=matching_course.get('lessons', []),
            total_lessons=len(matching_course.get('lessons', [])),
            formatted_outline=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Course outline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    logger.info("Starting up RAG System...")
    docs_path = "../docs"
    if os.path.exists(docs_path):
        logger.info("Loading initial documents...")
        try:
            courses, chunks = rag_system.add_course_folder(docs_path, clear_existing=False)
            logger.info(f"Loaded {courses} courses with {chunks} chunks")
        except Exception as e:
            logger.error(f"Error loading documents: {e}", exc_info=True)
    else:
        logger.warning(f"Documents folder not found at: {docs_path}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down RAG System...")
    rag_system.session_manager.shutdown()
    logger.info("RAG System shut down complete")

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
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")