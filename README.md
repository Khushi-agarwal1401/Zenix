# Zenix

Zenix is a modern, AI-powered chat application that provides an interactive and culturally nuanced conversational experience. 

It features two distinct personas:
- **Desi Persona:** A casual, friendly, and humorous persona that talks like a close friend.
- **Sarkari Persona:** A formal, helpful, and professional assistant.

## Features

- **Dual Personas:** Seamlessly toggle between "Desi" and "Sarkari" modes to change the tone of the conversation.
- **Instant Interceptors:** Fast, hardcoded frontend logic to instantly reply to greetings, well-being checks, and requests for jokes without hitting the backend.
- **Python AI Backend:** For complex queries, Zenix connects to a Python-based pipeline that includes intent classification, query rewriting (for RAG/Semantic Search), and LLM generation.
- **Modern UI:** Built with Next.js, React, and Tailwind CSS for a sleek, responsive, and accessible user experience.

## Tech Stack

### Frontend
- [Next.js](https://nextjs.org/) (App Router)
- React
- Tailwind CSS

### Backend
- Python 
- FastAPI (serving on `http://127.0.0.1:8000`)
- ChromaDB (for vector/semantic search)

## Getting Started

### 1. Start the Python Backend
Ensure you have Python installed and your virtual environment set up.

```bash
cd backend
pip install -r requirements.txt
# Run your FastAPI server (e.g., via uvicorn)
uvicorn main:app --reload --port 8000
```

### 2. Start the Next.js Frontend
In a new terminal window, install dependencies and start the development server:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the application.

## Project Structure

- `/src/components`: UI components including the `ChatInterface`, `PersonaToggle`, etc.
- `/src/lib/ai_service.ts`: The bridge between the frontend and backend, containing instant interceptor logic.
- `/backend/pipeline`: The Python backend pipeline for processing complex AI queries (e.g., `query_rewriter.py`).

## Contributing
Contributions and feedback are always welcome!
