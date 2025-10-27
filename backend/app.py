import warnings
import asyncio
import time

warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

import os
from typing import List, Optional, Dict, Any

from config import config
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from rag_system import RAGSystem

# Track document processing status
document_processing_status = {
    "is_processing": False,
    "total_courses": 0,
    "processed_courses": 0,
    "total_chunks": 0,
    "processed_chunks": 0,
    "errors": [],
    "start_time": None,
    "end_time": None,
}

# Initialize FastAPI app
app = FastAPI(
    title="Course Materials RAG System",
    root_path="",
    description="Fast RAG chatbot with optimized startup performance"
)

# Add trusted host middleware for proxy
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Enable CORS with proper settings for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Track startup metrics
startup_start_time = time.time()

print("🚀 Initializing RAG Chatbot with Performance Optimizations")
print("=" * 60)

# Initialize RAG system with lazy loading
print("🔧 Initializing RAG System...")
rag_system_init_start = time.time()
rag_system = RAGSystem(config)
rag_system_init_time = time.time() - rag_system_init_start
print(f"⚡ RAG System initialized in {rag_system_init_time:.2f}s")

# Pre-load components if configured
if config.PRELOAD_COMPONENTS:
    print("⚡ Pre-loading components (PRELOAD_COMPONENTS=true)...")
    preload_start = time.time()
    rag_system.initialize_components()
    preload_time = time.time() - preload_start
    print(f"✅ Components preloaded in {preload_time:.2f}s")
else:
    print("✅ RAG System ready (lazy loading enabled)")

print("\n🔧 Configuration:")
print(f"   └─ Lazy Loading: {config.LAZY_LOADING}")
print(f"   └─ Background Document Processing: {config.BACKGROUND_DOCUMENT_PROCESSING}")
print(f"   └─ Quick Start (skip docs): {config.QUICK_START}")
print(f"   └─ Embedding Model: {config.EMBEDDING_MODEL}")
print(f"   └─ Preload Components: {config.PRELOAD_COMPONENTS}")
print(f"   └─ Anthropic Model: {config.ANTHROPIC_MODEL}")

total_startup_time = time.time() - startup_start_time
print(f"\n📊 Startup completed in {total_startup_time:.2f}s")
print("\n🌟 Server starting...")
print("   └─ Available at: http://localhost:8000")
print("   └─ API docs: http://localhost:8000/docs")
print("   └─ Processing status: http://localhost:8000/api/processing-status")
print("=" * 60)


# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for course queries"""

    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for course queries"""

    answer: str
    sources: List[str]
    session_id: str


class CourseStats(BaseModel):
    """Response model for course statistics"""

    total_courses: int
    course_titles: List[str]


class ProcessingStatus(BaseModel):
    """Response model for document processing status"""

    is_processing: bool
    total_courses: int
    processed_courses: int
    total_chunks: int
    processed_chunks: int
    errors: List[str]
    start_time: Optional[float]
    end_time: Optional[float]
    processing_time: Optional[float] = None


# API Endpoints


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

        return QueryResponse(answer=answer, sources=sources, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
    """Get course analytics and statistics"""
    try:
        analytics = rag_system.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def process_documents_background():
    """Background task to process documents with detailed logging"""
    docs_path = "../docs"
    processing_start = time.time()

    if not os.path.exists(docs_path):
        error_msg = f"Docs directory not found: {docs_path}"
        document_processing_status["errors"].append(error_msg)
        document_processing_status["end_time"] = time.time()
        print(f"❌ Background processing failed: {error_msg}")
        return

    try:
        print("📚 Background document processing started...")

        # Track component loading time
        vector_store_start = time.time()
        _ = rag_system.vector_store  # This will trigger lazy loading
        vector_store_time = time.time() - vector_store_start
        print(f"   🧠 VectorStore loaded in {vector_store_time:.2f}s")

        # Process documents
        process_start = time.time()
        courses, chunks = rag_system.add_course_folder(
            docs_path, clear_existing=False
        )
        process_time = time.time() - process_start
        total_time = time.time() - processing_start

        # Update status
        document_processing_status["processed_courses"] = courses
        document_processing_status["processed_chunks"] = chunks
        document_processing_status["end_time"] = time.time()

        print(f"✅ Background processing completed:")
        print(f"   📄 Processed: {courses} courses, {chunks} chunks")
        print(f"   ⏱️  Processing time: {process_time:.2f}s")
        print(f"   🏁 Total background time: {total_time:.2f}s")

    except Exception as e:
        error_msg = f"Error in background processing: {e}"
        document_processing_status["errors"].append(error_msg)
        document_processing_status["end_time"] = time.time()
        total_time = time.time() - processing_start
        print(f"❌ {error_msg} (after {total_time:.2f}s)")
        import traceback
        print(f"   Stack trace: {traceback.format_exc()}")


@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup (configurable behavior)"""
    docs_path = "../docs"

    # Skip processing entirely if quick start is enabled
    if config.QUICK_START:
        print("🚀 Quick start mode - skipping document processing")
        return

    # Check if docs directory exists
    if not os.path.exists(docs_path):
        print(f"📁 Docs directory not found: {docs_path}")
        return

    # Configure processing based on settings
    if config.BACKGROUND_DOCUMENT_PROCESSING:
        print("📚 Starting background document processing...")
        document_processing_status["is_processing"] = True
        document_processing_status["start_time"] = time.time()

        # Count files first for status tracking
        try:
            files = [f for f in os.listdir(docs_path)
                    if os.path.isfile(os.path.join(docs_path, f))
                    and f.lower().endswith(('.pdf', '.docx', '.txt'))]
            document_processing_status["total_courses"] = len(files)
            print(f"   📄 Found {len(files)} course files to process")
            print(f"   🔄 Processing will continue in background")
            print(f"   📊 Check status at: /api/processing-status")
        except Exception as e:
            print(f"   ❌ Error counting files: {e}")

        # Start background processing
        asyncio.create_task(process_documents_background())

    else:
        # Traditional synchronous processing
        print("📚 Loading documents synchronously...")
        sync_start = time.time()
        try:
            courses, chunks = rag_system.add_course_folder(
                docs_path, clear_existing=False
            )
            sync_time = time.time() - sync_start
            print(f"✅ Loaded {courses} courses with {chunks} chunks in {sync_time:.2f}s")
        except Exception as e:
            print(f"❌ Error loading documents: {e}")


@app.get("/api/processing-status", response_model=ProcessingStatus)
async def get_processing_status():
    """Get current document processing status"""
    status = document_processing_status.copy()
    if status["start_time"] and status["end_time"]:
        status["processing_time"] = status["end_time"] - status["start_time"]
    return status


@app.post("/api/force-reload", response_model=Dict[str, Any])
async def force_reload_documents(background_tasks: BackgroundTasks):
    """Force reload all documents"""
    global document_processing_status

    if document_processing_status["is_processing"]:
        raise HTTPException(
            status_code=409,
            detail="Document processing already in progress"
        )

    docs_path = "../docs"
    if not os.path.exists(docs_path):
        raise HTTPException(
            status_code=404,
            detail=f"Docs directory not found: {docs_path}"
        )

    # Reset status
    document_processing_status = {
        "is_processing": True,
        "total_courses": 0,
        "processed_courses": 0,
        "total_chunks": 0,
        "processed_chunks": 0,
        "errors": [],
        "start_time": time.time(),
        "end_time": None,
    }

    # Clear existing data and reload
    try:
        rag_system.vector_store.clear_all_data()
        background_tasks.add_task(process_documents_background)
        return {"message": "Document reload started", "status": "started"}
    except Exception as e:
        document_processing_status["is_processing"] = False
        raise HTTPException(status_code=500, detail=str(e))


import os
from pathlib import Path

from fastapi.responses import FileResponse

# Custom static file handler with no-cache headers for development
from fastapi.staticfiles import StaticFiles


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
