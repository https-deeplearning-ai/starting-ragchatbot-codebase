import signal
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from models import Course, CourseChunk
from sentence_transformers import SentenceTransformer


@dataclass
class SearchResults:
    """Container for search results with metadata"""

    documents: List[str]
    metadata: List[Dict[str, Any]]
    distances: List[float]
    error: Optional[str] = None

    @classmethod
    def from_chroma(cls, chroma_results: Dict) -> "SearchResults":
        """Create SearchResults from ChromaDB query results"""
        return cls(
            documents=(
                chroma_results["documents"][0] if chroma_results["documents"] else []
            ),
            metadata=(
                chroma_results["metadatas"][0] if chroma_results["metadatas"] else []
            ),
            distances=(
                chroma_results["distances"][0] if chroma_results["distances"] else []
            ),
        )

    @classmethod
    def empty(cls, error_msg: str) -> "SearchResults":
        """Create empty results with error message"""
        return cls(documents=[], metadata=[], distances=[], error=error_msg)

    def is_empty(self) -> bool:
        """Check if results are empty"""
        return len(self.documents) == 0


class VectorStore:
    """Vector storage using ChromaDB for course content and metadata"""

    def __init__(self, chroma_path: str, embedding_model: str, max_results: int = 5):
        self.max_results = max_results
        self.embedding_model_name = embedding_model
        self.chroma_path = chroma_path

        print(f"🔧 Initializing VectorStore...")
        print(f"   Path: {chroma_path}")
        print(f"   Model: {embedding_model}")

        # Initialize ChromaDB client
        try:
            print("   📦 Initializing ChromaDB client...")
            self.client = chromadb.PersistentClient(
                path=chroma_path, settings=Settings(anonymized_telemetry=False)
            )
            print("   ✅ ChromaDB client initialized")
        except Exception as e:
            print(f"   ❌ Failed to initialize ChromaDB client: {e}")
            raise RuntimeError(f"ChromaDB initialization failed: {str(e)}")

        # Set up sentence transformer embedding function with timeout
        try:
            print("   🧠 Loading embedding model (this may take a moment)...")
            self.embedding_function = self._create_embedding_function_with_timeout(
                embedding_model, timeout=60
            )
            print("   ✅ Embedding function initialized")
        except Exception as e:
            print(f"   ❌ Failed to initialize embedding function: {e}")
            raise RuntimeError(f"Embedding function initialization failed: {str(e)}")

        # Create collections for different types of data
        try:
            print("   📚 Creating collections...")
            self.course_catalog = self._create_collection(
                "course_catalog"
            )  # Course titles/instructors
            self.course_content = self._create_collection(
                "course_content"
            )  # Actual course material
            print("   ✅ Collections created")
        except Exception as e:
            print(f"   ❌ Failed to create collections: {e}")
            raise RuntimeError(f"Collection creation failed: {str(e)}")

        print("   ✅ VectorStore initialization complete")

    def _create_embedding_function_with_timeout(
        self, model_name: str, timeout: int = 60
    ):
        """Create embedding function with timeout to prevent hanging"""

        def timeout_handler(signum, frame):
            raise TimeoutError(
                f"Embedding model loading timed out after {timeout} seconds"
            )

        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        try:
            print(f"      Loading model: {model_name}")
            start_time = time.time()

            # Try primary method
            embedding_function = (
                chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=model_name
                )
            )

            load_time = time.time() - start_time
            print(f"      ✅ Model loaded in {load_time:.1f} seconds")

            signal.alarm(0)  # Cancel timeout
            return embedding_function

        except TimeoutError:
            print(f"      ❌ Model loading timed out after {timeout} seconds")
            print(f"      This might be due to:")
            print(f"         - Slow network connection")
            print(f"         - Insufficient system resources")
            print(f"         - Large model size")
            raise RuntimeError(
                f"Failed to load embedding model '{model_name}' within {timeout} seconds. "
                "Consider using a lighter model or checking system resources."
            )

        except Exception as e:
            print(f"      ❌ Primary embedding function failed: {e}")

            # Try fallback method
            try:
                print("      🔄 Trying fallback embedding method...")
                start_time = time.time()

                # Pre-load the model directly
                model = SentenceTransformer(model_name)
                print(
                    f"      ✅ Direct model loading successful in {time.time() - start_time:.1f} seconds"
                )

                # Create custom embedding function
                class CustomEmbeddingFunction:
                    def __init__(self, model):
                        self.model = model

                    def __call__(self, texts):
                        return self.model.encode(texts).tolist()

                signal.alarm(0)  # Cancel timeout
                return CustomEmbeddingFunction(model)

            except Exception as fallback_error:
                print(
                    f"      ❌ Fallback embedding method also failed: {fallback_error}"
                )
                raise RuntimeError(
                    f"Failed to initialize embedding function using both primary and fallback methods. "
                    f"Primary error: {str(e)}, Fallback error: {str(fallback_error)}"
                )

        finally:
            # Restore original signal handler
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def _create_collection(self, name: str):
        """Create or get a ChromaDB collection"""
        return self.client.get_or_create_collection(
            name=name, embedding_function=self.embedding_function
        )

    def search(
        self,
        query: str,
        course_name: Optional[str] = None,
        lesson_number: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> SearchResults:
        """
        Main search interface that handles course resolution and content search.

        Args:
            query: What to search for in course content
            course_name: Optional course name/title to filter by
            lesson_number: Optional lesson number to filter by
            limit: Maximum results to return

        Returns:
            SearchResults object with documents and metadata
        """
        # Step 1: Resolve course name if provided
        course_title = None
        if course_name:
            course_title = self._resolve_course_name(course_name)
            if not course_title:
                return SearchResults.empty(f"No course found matching '{course_name}'")

        # Step 2: Build filter for content search
        filter_dict = self._build_filter(course_title, lesson_number)

        # Step 3: Search course content
        # Use provided limit or fall back to configured max_results
        search_limit = limit if limit is not None else self.max_results

        try:
            results = self.course_content.query(
                query_texts=[query], n_results=search_limit, where=filter_dict
            )
            return SearchResults.from_chroma(results)
        except Exception as e:
            return SearchResults.empty(f"Search error: {str(e)}")

    def _resolve_course_name(self, course_name: str) -> Optional[str]:
        """Use vector search to find best matching course by name"""
        try:
            results = self.course_catalog.query(query_texts=[course_name], n_results=1)

            if results["documents"][0] and results["metadatas"][0]:
                # Return the title (which is now the ID)
                return results["metadatas"][0][0]["title"]
        except Exception as e:
            print(f"Error resolving course name: {e}")

        return None

    def _build_filter(
        self, course_title: Optional[str], lesson_number: Optional[int]
    ) -> Optional[Dict]:
        """Build ChromaDB filter from search parameters"""
        if not course_title and lesson_number is None:
            return None

        # Handle different filter combinations
        if course_title and lesson_number is not None:
            return {
                "$and": [
                    {"course_title": course_title},
                    {"lesson_number": lesson_number},
                ]
            }

        if course_title:
            return {"course_title": course_title}

        return {"lesson_number": lesson_number}

    def add_course_metadata(self, course: Course):
        """Add course information to the catalog for semantic search"""
        import json

        course_text = course.title

        # Build lessons metadata and serialize as JSON string
        lessons_metadata = []
        for lesson in course.lessons:
            lessons_metadata.append(
                {
                    "lesson_number": lesson.lesson_number,
                    "lesson_title": lesson.title,
                    "lesson_link": lesson.lesson_link,
                }
            )

        self.course_catalog.add(
            documents=[course_text],
            metadatas=[
                {
                    "title": course.title,
                    "instructor": course.instructor,
                    "course_link": course.course_link,
                    "lessons_json": json.dumps(
                        lessons_metadata
                    ),  # Serialize as JSON string
                    "lesson_count": len(course.lessons),
                }
            ],
            ids=[course.title],
        )

    def add_course_content(self, chunks: List[CourseChunk]):
        """Add course content chunks to the vector store"""
        if not chunks:
            return

        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "course_title": chunk.course_title,
                "lesson_number": chunk.lesson_number,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ]
        # Use title with chunk index for unique IDs
        ids = [
            f"{chunk.course_title.replace(' ', '_')}_{chunk.chunk_index}"
            for chunk in chunks
        ]

        self.course_content.add(documents=documents, metadatas=metadatas, ids=ids)

    def clear_all_data(self):
        """Clear all data from both collections"""
        try:
            self.client.delete_collection("course_catalog")
            self.client.delete_collection("course_content")
            # Recreate collections
            self.course_catalog = self._create_collection("course_catalog")
            self.course_content = self._create_collection("course_content")
        except Exception as e:
            print(f"Error clearing data: {e}")

    def get_existing_course_titles(self) -> List[str]:
        """Get all existing course titles from the vector store"""
        try:
            # Get all documents from the catalog
            results = self.course_catalog.get()
            if results and "ids" in results:
                return results["ids"]
            return []
        except Exception as e:
            print(f"Error getting existing course titles: {e}")
            return []

    def get_course_count(self) -> int:
        """Get the total number of courses in the vector store"""
        try:
            results = self.course_catalog.get()
            if results and "ids" in results:
                return len(results["ids"])
            return 0
        except Exception as e:
            print(f"Error getting course count: {e}")
            return 0

    def get_all_courses_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all courses in the vector store"""
        import json

        try:
            results = self.course_catalog.get()
            if results and "metadatas" in results:
                # Parse lessons JSON for each course
                parsed_metadata = []
                for metadata in results["metadatas"]:
                    course_meta = metadata.copy()
                    if "lessons_json" in course_meta:
                        course_meta["lessons"] = json.loads(course_meta["lessons_json"])
                        del course_meta[
                            "lessons_json"
                        ]  # Remove the JSON string version
                    parsed_metadata.append(course_meta)
                return parsed_metadata
            return []
        except Exception as e:
            print(f"Error getting courses metadata: {e}")
            return []

    def get_course_link(self, course_title: str) -> Optional[str]:
        """Get course link for a given course title"""
        try:
            # Get course by ID (title is the ID)
            results = self.course_catalog.get(ids=[course_title])
            if results and "metadatas" in results and results["metadatas"]:
                metadata = results["metadatas"][0]
                return metadata.get("course_link")
            return None
        except Exception as e:
            print(f"Error getting course link: {e}")
            return None

    def get_lesson_link(self, course_title: str, lesson_number: int) -> Optional[str]:
        """Get lesson link for a given course title and lesson number"""
        import json

        try:
            # Get course by ID (title is the ID)
            results = self.course_catalog.get(ids=[course_title])
            if results and "metadatas" in results and results["metadatas"]:
                metadata = results["metadatas"][0]
                lessons_json = metadata.get("lessons_json")
                if lessons_json:
                    lessons = json.loads(lessons_json)
                    # Find the lesson with matching number
                    for lesson in lessons:
                        if lesson.get("lesson_number") == lesson_number:
                            return lesson.get("lesson_link")
            return None
        except Exception as e:
            print(f"Error getting lesson link: {e}")
