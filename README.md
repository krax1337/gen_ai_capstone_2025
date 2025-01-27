# Hooli Helpdesk - AI-Powered Support System

## Overview

Hooli Helpdesk is an intelligent support system that leverages AI to provide automated assistance while maintaining a record of support tickets. The system uses OpenAI's GPT models for natural language processing and ChromaDB for efficient semantic search capabilities.

## Features

- 🤖 AI-powered chatbot for instant support
- 📊 Real-time ticket tracking and management
- 🔍 Semantic search functionality using ChromaDB
- 🔄 Integration with Telegram for notifications
- 💬 Interactive chat interface
- 📝 Ticket history and status tracking

## Technology Stack

- Python 3.10+
- Streamlit for frontend
- OpenAI GPT-4 for natural language processing
- ChromaDB for vector database
- Pandas for data handling
- Sentence Transformers for text embeddings

## System Architecture

The system follows a modular architecture with the following components:

1. **User Interface**: Streamlit-based web interface with chat window and ticket management
2. **AI Processing**: OpenAI GPT model integration for natural language understanding
3. **Database Layer**: ChromaDB for semantic search and ticket storage
4. **Notification System**: Telegram integration for alerts and updates

## Running the Application (Docker)

1. Clone the repository
2. Install Docker and Docker Compose
3. Run `docker compose up --build` to start the application
4. Access the application at `http://localhost:3434`

## Running the Application (Local)

1. Clone the repository
2. Install Python 3.12
3. Run `python3 -m venv .venv` to create a virtual environment
4. Run `source .venv/bin/activate` to activate the virtual environment
5. Run `pip install -r requirements.txt` to install the dependencies
6. Run `streamlit run main.py` to start the application
