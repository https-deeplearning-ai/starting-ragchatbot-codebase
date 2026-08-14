---
name: rebuild-index
description: Clear the ChromaDB vector store and re-ingest all course transcripts from docs/. Use after editing a file in docs/, changing CHUNK_SIZE/CHUNK_OVERLAP/EMBEDDING_MODEL in backend/config.py, or whenever the index looks stale — normal server startup skips any course whose title already exists in the course_catalog collection, so those changes otherwise have no effect.
---

Rebuild the ChromaDB index for this RAG chatbot from scratch.

1. Make sure the dev server (`uvicorn app:app`) is stopped — ChromaDB's persistent client can't be written to from two processes at once.
2. From the `backend/` directory, run:
   ```bash
   uv run python -c "
   from config import config
   from rag_system import RAGSystem

   rag = RAGSystem(config)
   courses, chunks = rag.add_course_folder('../docs', clear_existing=True)
   print(f'Rebuilt index: {courses} courses, {chunks} chunks')
   "
   ```
   `clear_existing=True` calls `VectorStore.clear_all_data()` before re-ingesting, so this reprocesses every file in `docs/` regardless of what's already indexed — that's what makes it pick up edits to existing transcripts or new chunking settings.
3. Restart the dev server. Startup ingestion will now see an empty `course_catalog` and re-load everything fresh (this step is redundant with step 2 immediately after a rebuild, but is what the normal `add_course_folder(clear_existing=False)` startup path does going forward).
