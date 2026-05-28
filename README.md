# GitHub Analyzer

A backend system that analyzes Git repositories using asynchronous workflows, vector embeddings, and LLM-powered summarization to generate semantic code insights, repository understanding, followed by chat.

## Features

* Analyze any public GitHub repository
* Summarize repository .
* Generate AI-powered repository summaries
* Semantic search across repository code using embeddings
* Store and query vector embeddings with PostgreSQL + pgvector
* Async background processing with task queues

## Getting Started

### Prerequisites

* Python 3.11+
* PostgreSQL
* pgvector extension enabled
* Groq Personal Access Token
* Cohere Personal Access Token
* 
## Installation

```bash
git clone https://github.com/your-username/github-analyzer.git
cd github-analyzer
```

Create and activate a virtual environment:

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_personal_access_token
COHERE_API_KEY=your_personal_access_token
#DEBUG=True

```

Enable pgvector in PostgreSQL:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Run migrations:

```bash
python manage.py migrate
```

Start the development server:

```bash
python manage.py runserver
```

## Usage

1. Open the application in your browser
2. Enter a public GitHub repository URL or `owner/repo` name
3. Start the analysis
4. Explore repository insights, summaries, contributors, and activity trends

## Tech Stack

* Django
* PostgreSQL
* pgvector
* GitHub REST API 
* Python
* Celery (background task processing) (Setup is present ,But not used)
* Vector embeddings for semantic repository understanding


This project is licensed under the MIT License.
