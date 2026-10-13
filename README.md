# PyForge

**A Python-powered job execution and automation platform.**

PyForge is a backend engineering project for creating, executing, tracking, and persisting jobs through a modular execution engine. It combines a command-line interface, pluggable executors, concurrency utilities, TCP networking, SQLite persistence, and a REST API built with FastAPI.

The project is being developed incrementally, with automated tests and a focus on Python fundamentals, clean architecture, concurrency, networking, and service design.

## Features

### Job management
- Create jobs with a name, command, timeout, and metadata.
- Track job lifecycle states such as pending, running, success, failure, timeout, and cancellation.
- Retrieve, list, and delete jobs.
- Store execution results, including standard output, standard error, exit code, timestamps, and errors.

### Execution engine
- Synchronous operating-system command execution.
- Timeout and missing-command error handling.
- Pluggable executor architecture with a registry.
- Thread-based execution of multiple jobs.
- Process-pool runner for parallel Python callables.
- Async task runner with bounded concurrency.

### Persistence
- Repository abstraction separating storage from business logic.
- In-memory repository for testing and lightweight use.
- SQLite repository for persistent job and result storage.
- JSON serialization for command arguments and metadata.
- Parameterized SQL queries and relational job/result storage.

### Command-line interface
- Create, list, inspect, execute, retrieve results, and delete jobs.
- Execute multiple jobs concurrently.
- Select an executor through the plugin architecture.
- Configure the SQLite database path.

### Networking
- Asynchronous TCP server and client.
- Newline-delimited JSON message protocol.
- Message-size limits and protocol validation.
- Ping and echo commands.
- Error responses for invalid messages and unsupported commands.

### REST API
- FastAPI application with automatically generated OpenAPI documentation.
- Endpoints for creating, listing, retrieving, executing, and deleting jobs.
- Pydantic request validation.
- Health endpoint.
- API-key authentication for job-management routes.
- Dependency-injected manager for isolated integration tests.

## Architecture

```text
                         Clients
                    CLI / HTTP clients
                            |
               +------------+------------+
               |                         |
          CLI interface             FastAPI
               |                         |
               +------------+------------+
                            |
                        JobManager
                            |
             +--------------+--------------+
             |                             |
       Executor plugins               Repository
             |                             |
     +-------+--------+             +------+------+
     |       |        |             |             |
   Sync    Thread   Async/Process  Memory        SQLite
     |
 OS command execution

Additional module:
TCP client/server with JSON message protocol
```

The components have distinct responsibilities:

- **Domain models** represent jobs, statuses, and results.
- **JobManager** coordinates job operations and persistence.
- **Executors** perform work.
- **Repositories** store and retrieve jobs and results.
- **CLI and API layers** expose functionality to users and clients.

## Technology stack

- Python 3.10+
- FastAPI and Pydantic
- Uvicorn
- SQLite
- `subprocess`
- `concurrent.futures`
- `asyncio`
- TCP sockets and newline-delimited JSON
- pytest
- Git and GitHub

## Project milestones

| Version | Milestone | Implemented scope |
|---|---|---|
| V0 | Domain foundation | Job and result models, job statuses, base exceptions |
| V1 | Execution engine | Synchronous command execution and execution results |
| V2 | Serialization | JSON-compatible representation of job data |
| V3 | Persistence | Repository abstraction, in-memory storage, SQLite storage |
| V4 | CLI | Job lifecycle commands and database configuration |
| V5 | Plugin architecture | Executor plugin interface, registry, built-in executor, plugin discovery |
| V6 | Thread concurrency | Concurrent job execution and `run-many` |
| V7 | Process execution utilities | Process-pool runner for Python callables |
| V8 | Async execution utilities | Async task runner with a concurrency limit |
| V9 | Networking | TCP server/client, JSON protocol, message validation |
| V10 | REST API | FastAPI endpoints, request validation, integration tests |
| V11 | Authentication | API-key protection for job-management endpoints |

These milestones describe the current development history. Passing tests verifies implemented behavior, but does not by itself mean the platform is production-hardened.

## Requirements

- Python 3.10 or later
- pip
- Git

## Setup

Clone the repository:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd forge
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the runtime and test dependencies:

```bash
python -m pip install fastapi "uvicorn[standard]" python-dotenv httpx pytest
```

If the project dependencies are declared in `pyproject.toml`, you can also install the project itself with:

```bash
python -m pip install -e .
```

Configure your local environment:

```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder with a newly generated secret. Never commit the real `.env` file.

## Running tests

Run the complete test suite:

```bash
PYTHONPATH=src python -m pytest -v
```

Run API integration tests:

```bash
PYTHONPATH=src python -m pytest tests/integration/test_api.py -v
```

Run TCP integration tests:

```bash
PYTHONPATH=src python -m pytest tests/integration/test_tcp_server.py -v
```

Run networking protocol unit tests:

```bash
PYTHONPATH=src python -m pytest tests/unit/test_network_protocol.py -v
```

The test suite includes unit and integration tests for the project's domain, storage, execution, concurrency, networking, and API components.

## Running the REST API

Ensure your `.env` file contains a configured `PYFORGE_API_KEY`.

Start the server:

```bash
PYTHONPATH=src python -m uvicorn pyforge.api:app --reload
```

Open the interactive API documentation:

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json
- Health check: http://127.0.0.1:8000/health

### Example requests

Health check:

```bash
curl http://127.0.0.1:8000/health
```

List jobs with authentication:

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://127.0.0.1:8000/jobs
```

Create a job:

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "name": "hello",
    "command": ["python3", "-c", "print(\"Hello from PyForge\")"],
    "timeout": 10
  }'
```

Use the returned job ID to execute it:

```bash
curl -X POST \
  "http://127.0.0.1:8000/jobs/YOUR_JOB_ID/run" \
  -H "X-API-Key: YOUR_API_KEY"
```

## Command-line interface

Run commands from the project root with the source directory on the Python path:

```bash
PYTHONPATH=src python -m pyforge --help
```

The CLI supports job creation, listing, inspection, execution, result retrieval, deletion, and concurrent execution. Use the CLI help output to inspect the available arguments and commands.

## Project structure

```text
forge/
├── src/
│   └── pyforge/
│       ├── domain/
│       ├── engine/
│       ├── networking/
│       ├── plugins/
│       ├── storage/
│       ├── api.py
│       ├── cli.py
│       ├── manager.py
│       └── __main__.py
├── tests/
│   ├── unit/
│   └── integration/
├── examples/
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

The directory listing above is representative; the exact files may evolve as development continues.

## Security notes

PyForge can execute operating-system commands. Treat this as a privileged capability.

- Keep the development API bound to `127.0.0.1`.
- Never commit API keys or other credentials.
- API-key authentication is not a substitute for authorization, process isolation, or resource limits.
- Do not expose the service to untrusted users or the public internet without further security controls.
- Only load trusted external executor plugins.

## Roadmap

Planned improvements include:

- Fine-grained authorization and role/permission management.
- A React and TypeScript dashboard for visual job management.
- Scheduling and recurring jobs.
- Structured logging, metrics, and operational observability.
- Packaging, Docker, and CI/CD.
- Resource limits, process isolation, resilience, and production hardening.

## Development philosophy

PyForge is built milestone by milestone. Each milestone introduces a concrete capability, reinforces Python engineering concepts, and is validated with tests before further expansion.

The goal is to understand not only how to use frameworks, but also how job execution, storage, concurrency, networking, API design, and service architecture fit together.