# RAG Chatbot Failure Analysis and Proposed Fixes

## Issue Identified
**Root Cause**: Sentence-transformers model loading is timing out/failing during VectorStore initialization, causing the entire RAG system to fail and return "query failed" for content-related questions.

## Evidence from Tests

1. **Basic Component Tests**: ✅ All individual modules import correctly
2. **Model Creation Tests**: ✅ All data models (Course, Lesson, CourseChunk) work correctly
3. **Configuration Tests**: ✅ Config loads properly with valid API key
4. **VectorStore Initialization**: ❌ **FAILS** - Times out during sentence-transformers model loading

## Specific Failure Point

The issue occurs in `vector_store.py` at line 46-48:
```python
self.embedding_function = chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=embedding_model
)
```

The sentence-transformers model `all-MiniLM-L6-v2` is taking too long to load or failing to initialize.

## Proposed Fixes

### 1. **Immediate Fix - Add Error Handling and Timeouts**

Add timeout and error handling to VectorStore initialization:

```python
# In vector_store.py
import signal
from contextlib import contextmanager

@contextmanager
def timeout_context(seconds):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

# In VectorStore.__init__
try:
    with timeout_context(30):  # 30 second timeout
        self.embedding_function = chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
except TimeoutError:
    raise RuntimeError(f"Failed to load embedding model '{embedding_model}' within timeout. "
                      "This may be due to network issues or insufficient resources.")
except Exception as e:
    raise RuntimeError(f"Failed to initialize embedding function: {str(e)}")
```

### 2. **Configuration Fix - Use a Lighter Model**

Change the embedding model to a lighter/faster option:

```python
# In config.py
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # Current (slow)
# EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"  # Try full name
# EMBEDDING_MODEL: str = "multi-qa-MiniLM-L6-cos-v1"  # Faster alternative
```

### 3. **Caching Fix - Pre-download Models**

Add model pre-loading and caching:

```python
# In vector_store.py, before initializing ChromaDB
def _ensure_model_cached(self, model_name: str):
    """Ensure the embedding model is downloaded and cached"""
    try:
        from sentence_transformers import SentenceTransformer
        print(f"Pre-loading embedding model: {model_name}")
        model = SentenceTransformer(model_name)
        print("✅ Embedding model cached successfully")
    except Exception as e:
        print(f"❌ Failed to cache embedding model: {e}")
        raise
```

### 4. **Fallback Fix - Alternative Embedding Function**

Provide a fallback embedding function:

```python
# In vector_store.py
def _create_embedding_function(self, model_name: str):
    """Create embedding function with fallback options"""
    try:
        # Try primary method
        return chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
    except Exception as e:
        print(f"Primary embedding function failed: {e}")

        # Try alternative method
        try:
            from sentence_transformers import SentenceTransformer

            class CustomEmbeddingFunction:
                def __init__(self, model_name):
                    self.model = SentenceTransformer(model_name)

                def __call__(self, texts):
                    return self.model.encode(texts).tolist()

            return CustomEmbeddingFunction(model_name)
        except Exception as e2:
            print(f"Fallback embedding function failed: {e2}")
            raise RuntimeError(f"All embedding function options failed: {e}, {e2}")
```

### 5. **Startup Fix - Lazy Loading**

Change to lazy loading pattern:

```python
# In vector_store.py
class VectorStore:
    def __init__(self, chroma_path: str, embedding_model: str, max_results: int = 5):
        self.max_results = max_results
        self.chroma_path = chroma_path
        self.embedding_model_name = embedding_model
        self._embedding_function = None
        self._client = None

        # Initialize collections later
        self.course_catalog = None
        self.course_content = None

    @property
    def embedding_function(self):
        """Lazy load embedding function"""
        if self._embedding_function is None:
            self._initialize_embedding_function()
        return self._embedding_function

    def _initialize_embedding_function(self):
        """Initialize embedding function when first needed"""
        # Implementation with timeout and error handling
        pass

    def _ensure_initialized(self):
        """Ensure all components are initialized"""
        if self._client is None:
            self._initialize_client()
        if self.course_catalog is None:
            self._initialize_collections()
```

### 6. **Environment Fix - Resource Limits**

Check and possibly adjust environment:

```python
# Add to requirements or check system resources
import psutil
import os

def check_system_resources():
    """Check if system has sufficient resources"""
    memory_gb = psutil.virtual_memory().total / (1024**3)
    print(f"Available memory: {memory_gb:.1f} GB")

    if memory_gb < 4:
        print("⚠️  Low memory detected, this may cause model loading issues")
        print("Consider using a lighter embedding model or increasing system resources")

    # Check disk space
    disk_free_gb = psutil.disk_usage('.').free / (1024**3)
    print(f"Available disk space: {disk_free_gb:.1f} GB")

    if disk_free_gb < 2:
        print("⚠️  Low disk space, model caching may fail")
```

## Implementation Priority

### High Priority (Immediate Fix)
1. **Add timeout and error handling** to VectorStore initialization
2. **Implement lazy loading** to defer model loading until actually needed
3. **Add proper error messages** to help diagnose issues

### Medium Priority (Performance Fix)
4. **Try alternative embedding models** that load faster
5. **Add model pre-loading** with progress indicators
6. **Implement fallback options**

### Low Priority (Robustness)
7. **Add system resource checks**
8. **Implement model caching strategies**
9. **Add monitoring and logging**

## Testing Strategy

After implementing fixes:

1. **Unit tests** for each fix with mocked dependencies
2. **Integration tests** with actual model loading
3. **Performance tests** to measure loading times
4. **Error handling tests** to verify graceful failures

## Expected Outcome

With these fixes, the RAG system should:

1. **Load successfully** without timing out
2. **Provide clear error messages** if initialization fails
3. **Have fallback options** for different environments
4. **Load faster** with optimized model selection
5. **Be more robust** in resource-constrained environments

The "query failed" issue should be resolved, and users should be able to successfully query course content.