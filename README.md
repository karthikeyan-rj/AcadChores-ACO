# Autonomous Computer Operator (ACO)

An AI-powered autonomous agent that plans and executes multi-step workflows on your computer using natural language. Just tell ACO what you want to do, and it figures out the steps — browsing the web, managing files, running terminal commands, and more.

## Demo

```
User: "create a palindrome program in C++ on my desktop"
ACO:  [Plan] → [Write palindrome.cpp] → [Compile with g++] → [Run executable]

User: "what is the disk space on my computer"
ACO:  [Plan] → [Run Get-Volume] → [Show results]

User: "send email to john@example.com subject Meeting body Let's meet tomorrow"
ACO:  [Plan] → [Draft email] → [Confirm with user] → [Send via Gmail]
```

## Features

### 5 Specialized Agents
| Agent | Capabilities |
|-------|-------------|
| **Browser** | Navigate, click, fill forms, scrape text, summarize pages |
| **Desktop** | Click, type, press keys on any application |
| **Terminal** | Execute PowerShell/cmd commands |
| **File** | Read, write, delete, list, search files |
| **Vision** | Capture screen, find text on screen |

### Multi-Language Code Generation
Generate, compile, and run code in **15+ languages**: Python, C, C++, Java, JavaScript, TypeScript, Go, Rust, PHP, Ruby, HTML, CSS, Bash, Kotlin, Swift, C#, and more.

### Smart Planning
- **LLM-based intent extraction** — understands natural language, not just keywords
- **Multi-step workflows** — chains actions across agents automatically
- **Language-agnostic** — detects programming language from context, not hardcoded rules

### Safety & Permissions
- **Pre-execution confirmation** — destructive commands require approval
- **File write confirmation** — asks before creating files
- **Email draft review** — edit before sending
- **Permission system** — granular control per agent/action

### Built-in Recovery
- Automatic retry on failure
- Alternative approach generation
- Verification of execution results
- Confidence scoring

## Tech Stack

**Backend**
- Python 3.10+
- FastAPI + LangGraph (workflow orchestration)
- Ollama (local LLM: qwen2.5-coder:7b)
- MongoDB Atlas (persistent storage)
- Playwright (browser automation)

**Frontend**
- Next.js 14 + TypeScript
- Tailwind CSS
- Real-time WebSocket events
- Glassmorphism UI

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Ollama (installed and running)
- MongoDB Atlas account (or local MongoDB)

### 1. Clone the repository
```bash
git clone https://github.com/santhoshraj706/Autonomous-Computer-Operator.git
cd Autonomous-Computer-Operator
```

### 2. Set up the backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 3. Configure environment
Create `backend/.env`:
```env
MONGODB_URL=your_mongodb_connection_string
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
```

### 4. Set up Ollama
```bash
ollama pull qwen2.5-coder:7b
```

### 5. Start the backend
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 6. Set up the frontend
```bash
cd frontend
npm install
npm run dev
```

### 7. Open the app
Navigate to [http://localhost:3000](http://localhost:3000)

## Usage Examples

### System Information
```
what is the disk space on my computer
show my IP address
list running processes
who am i
```

### File Operations
```
create a file called notes.txt on my desktop
list all files on my desktop
find all PDF files in my documents
```

### Code Generation
```
create palindrome in C++ on my desktop
write a python script called calculator.py
create a hello world program in java
```

### Web Browsing
```
open google and search for python tutorials
go to github.com and find trending repositories
summarize this webpage
```

### Email
```
send email to john@example.com subject Meeting body Let's meet tomorrow
```

### System Commands
```
run ipconfig in terminal
format the drive (requires confirmation)
shutdown now (requires confirmation)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│  Chat UI │ Execution Panel │ Permission Modal │ Live Console │
└───────────────────────────┬─────────────────────────────────┘
                            │ WebSocket + REST
┌───────────────────────────┴─────────────────────────────────┐
│                      Backend (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│  Planner (LangGraph)  │  Worker Pool  │  Permission Guard   │
├─────────────────────────────────────────────────────────────┤
│  LLM Metadata Extraction (filename, location, language)     │
├─────────────────────────────────────────────────────────────┤
│  Agent Dispatcher                                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐ │
│  │ Browser  │ Desktop  │ Terminal │   File   │  Vision  │ │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Language Engine (detection, compilation, execution)        │
│  Recovery Engine │ Verification Engine │ Event Bus          │
└─────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │    MongoDB    │
                    │    Ollama     │
                    │   Playwright  │
                    └───────────────┘
```

## Configuration

Edit `backend/app/core/config.py`:

```python
# Permission defaults
DEFAULT_PERM_BROWSER = "allow"      # allow | ask | block
DEFAULT_PERM_TERMINAL = "allow"
DEFAULT_PERM_DESKTOP = "ask"
DEFAULT_PERM_FILE_WRITE = "ask"
DEFAULT_PERM_FILE_DELETE = "block"

# Worker pool
MAX_WORKERS = 3
```

## Project Structure

```
Acad/
├── backend/
│   ├── app/
│   │   ├── ai/              # LLM providers (Ollama, OpenAI, etc.)
│   │   ├── api/v1/          # REST endpoints
│   │   ├── core/            # Config, security, event bus
│   │   ├── services/
│   │   │   ├── planner.py           # LangGraph workflow planner
│   │   │   ├── agent_dispatcher.py  # Agent execution
│   │   │   ├── language_engine.py   # Language detection & execution
│   │   │   └── worker.py           # Task worker pool
│   │   ├── recovery/        # Error recovery engine
│   │   └── verification/    # Result verification
│   ├── test_*.py            # Regression tests
│   └── requirements.txt
├── frontend/
│   ├── src/app/             # Next.js pages
│   ├── src/components/      # UI components
│   └── src/lib/             # API client, hooks
└── README.md
```

## License

MIT License - see [LICENSE](LICENSE) for details.
