from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Union
import traceback
from logger import get_logger

logger = get_logger(__name__)


class RAGSystemError(Exception):
    """Base exception for RAG system errors"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or "RAG_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class DocumentProcessingError(RAGSystemError):
    """Raised when document processing fails"""
    def __init__(self, message: str, file_path: str = None):
        super().__init__(message, "DOCUMENT_PROCESSING_ERROR", {"file_path": file_path})


class VectorStoreError(RAGSystemError):
    """Raised when vector store operations fail"""
    def __init__(self, message: str, operation: str = None):
        super().__init__(message, "VECTOR_STORE_ERROR", {"operation": operation})


class AIGenerationError(RAGSystemError):
    """Raised when AI generation fails"""
    def __init__(self, message: str, model: str = None):
        super().__init__(message, "AI_GENERATION_ERROR", {"model": model})


class SearchError(RAGSystemError):
    """Raised when search operations fail"""
    def __init__(self, message: str, query: str = None):
        super().__init__(message, "SEARCH_ERROR", {"query": query})


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation errors"""
    logger.warning(f"Validation error for {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "error_code": "VALIDATION_ERROR",
            "details": exc.errors(),
            "message": "Request validation failed"
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with proper logging"""
    logger.warning(f"HTTP {exc.status_code} for {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail
        }
    )


async def rag_system_exception_handler(request: Request, exc: RAGSystemError) -> JSONResponse:
    """Handle custom RAG system errors"""
    logger.error(f"RAG System error for {request.url}: {exc.message}",
                extra={"error_code": exc.error_code, "details": exc.details})
    return JSONResponse(
        status_code=500,
        content={
            "error": "RAG System Error",
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions"""
    logger.error(f"Unhandled error for {request.url}: {str(exc)}",
                exc_info=True,
                extra={"traceback": traceback.format_exc()})
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred"
        }
    )


def log_request_response(request: Request, response_code: int, processing_time: float = None):
    """Log request and response information"""
    log_data = {
        "method": request.method,
        "url": str(request.url),
        "status_code": response_code,
    }

    if processing_time:
        log_data["processing_time"] = f"{processing_time:.3f}s"

    if response_code >= 400:
        logger.warning("Request completed with error", extra=log_data)
    else:
        logger.info("Request completed successfully", extra=log_data)