# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Claude (via AWS Bedrock) for AI generation, and Cohere Embed Multilingual v3 (via AWS Bedrock) for embeddings.

## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- AWS credentials configured with access to Bedrock (Claude and Cohere inference profiles)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**

   Copy `.env.example` to `.env` and fill in your Bedrock inference profile ARNs:
   ```bash
   ANTHROPIC_MODEL=arn:aws:bedrock:<region>:<account-id>:application-inference-profile/<profile-id>
   EMBED_MODEL=arn:aws:bedrock:<region>:<account-id>:application-inference-profile/<profile-id>
   AWS_PROFILE=your-aws-profile-name  # if not already set in your environment
   ```

## Running the Application

```bash
./run.sh
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
