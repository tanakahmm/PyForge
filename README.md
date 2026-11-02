# PyForge

**A Python-powered job execution, automation, and scheduling platform.**

PyForge is a backend and systems engineering project for creating, executing, tracking, scheduling, and persisting jobs. It provides multiple interfaces for interacting with jobs and explores core Python engineering concepts including process execution, concurrency, asynchronous programming, networking, persistence, API design, authentication, authorization, scheduling, observability, and automated testing.

The project was developed incrementally through versioned milestones, with each stage introducing a new engineering concept and validating it through automated tests.

---

## What is PyForge?

At its core, PyForge manages the lifecycle of executable jobs.

A user can provide a command such as:

```text
["python3", "-c", "print('Hello from PyForge')"]
```

PyForge can then:

1. Create and validate a job.
2. Store the job in a repository.
3. Execute the command through an executor.
4. Capture standard output, standard error, exit status, timing, and errors.
5. Persist the execution result.
6. Expose the job and its result through the CLI or REST API.
7. Execute multiple jobs concurrently or schedule jobs for future execution.

---

# Features

## Job management

- Create jobs with a name, command, timeout, and metadata.
- Track job lifecycle and execution states.
- Retrieve individual jobs and list stored jobs.
- Delete jobs and associated execution data.
- Store execution results including standard output, standard error, exit codes, timestamps, and errors.

## Execution engine

- Execute operating-system commands synchronously.
- Handle successful execution, command failures, missing commands, and timeouts.
- Use a pluggable executor architecture.
- Register and create executors through a plugin registry.
- Execute multiple jobs concurrently using worker threads.

## Concurrency utilities

PyForge explores multiple Python concurrency models:

- Thread-based concurrent job execution.
- Process-pool execution for Python callables.
- Async task execution with bounded concurrency.
- Ordered result collection.
- Validation of concurrency and worker limits.

## Persistence

- Repository abstraction separating storage from application logic.
- In-memory repository for lightweight use and testing.
- SQLite repository for persistent storage.
- Persistent job and execution-result storage.
- JSON serialization for structured fields.
- Parameterized SQL queries.
- Repository behavior tested across application restarts.

## Command-line interface

The CLI supports:

- Job creation.
- Listing jobs.
- Inspecting jobs.
- Executing jobs.
- Retrieving execution results.
- Deleting jobs.
- Concurrent execution workflows.
- Database-path configuration.

## Networking

PyForge includes an asynchronous TCP networking module with:

- TCP server and client support.
- Newline-delimited JSON message framing.
- Message-size limits.
- JSON and protocol validation.
- Ping and echo commands.
- Error handling for malformed or unsupported messages.

## REST API

The FastAPI application provides:

- Job creation and validation.
- Job retrieval and listing.
- Job execution.
- Result retrieval.
- Job deletion.
- Health and service endpoints.
- OpenAPI documentation.
- Dependency-injected application components for isolated tests.

## Security

PyForge includes application-level security concepts such as:

- API-key authentication for protected endpoints.
- Authentication dependencies.
- Secure API-key comparison.
- Authorization and permission concepts for controlled operations.
- Environment-based configuration for secrets.

> PyForge can execute operating-system commands. It should be treated as a privileged development tool and should not be exposed to untrusted users without additional security controls.

## Scheduling

The scheduling subsystem introduces time-based job execution concepts:

- Create and manage recurring schedules.
- Track the next execution time.
- Represent individual schedule occurrences.
- Use timezone-aware UTC timestamps.
- Track occurrence states and execution outcomes.
- Enable and disable schedules.
- Record missed or interrupted executions.

## Observability

PyForge includes operational concepts for understanding application behavior:

- Structured application logging.
- Request and correlation identifiers.
- Health and readiness checks.
- Metrics and execution visibility.
- Error reporting and diagnostic information.

---

# Architecture

```text
                              Clients
                 CLI / HTTP Clients / Scheduler
                              |
                 +------------+------------+
                 |                         |
                CLI                     FastAPI
                 |                         |
                 +------------+------------+
                              |
                          JobManager
                              |
              +---------------+---------------+
              |                               |
          Executors                        Repository
              |                               |
       Plugin Registry                 +-----+------+
              |                        |            |
        Sync Executor              Memory        SQLite
              |
         subprocess
              |
       Operating System
              |
          JobResult


Additional components:

Scheduler
    |
Schedule -> Occurrence -> Job Execution

Networking
    |
TCP Client <-> JSON Protocol <-> TCP Server

Observability
    |
Logging + Metrics + Health / Readiness
```

## Architectural responsibilities

### Domain layer

Represents the core concepts of the application:

- Jobs.
- Execution results.
- Statuses.
- Schedules.
- Schedule occurrences.
- Domain-specific errors.

### JobManager

Coordinates application workflows.

It manages operations such as:

- Creating jobs.
- Retrieving jobs.
- Executing jobs.
- Persisting updated job state.
- Storing execution results.
- Coordinating concurrent execution.

### Executors

Executors are responsible for performing work.

The executor abstraction allows execution strategies to be extended without tightly coupling the application to one implementation.

### Repositories

Repositories separate application logic from storage implementation.

The manager interacts with a repository abstraction rather than directly writing database queries.

### Interfaces

The CLI and REST API expose the application to users and external clients while keeping business logic inside the application layers.

---

# Technology Stack

- **Python 3.10+**
- **FastAPI**
- **Pydantic**
- **Uvicorn**
- **SQLite**
- **pytest**
- **subprocess**
- **concurrent.futures**
- **asyncio**
- **TCP sockets**
- **JSON**
- **Git and GitHub**

---

# Project Milestones

| Version | Milestone | Implemented scope |
|---|---|---|
| V0 | Domain foundation | Job models, execution results, statuses, and domain exceptions |
| V1 | Execution engine | Synchronous command execution and result capture |
| V2 | Serialization | JSON-compatible serialization of jobs and results |
| V3 | Persistence | Repository abstraction, in-memory storage, and SQLite persistence |
| V4 | CLI | Command-line job management and execution workflows |
| V5 | Plugin architecture | Executor abstraction, registry, and extensible execution strategies |
| V6 | Thread concurrency | Concurrent job execution with worker threads |
| V7 | Process execution | Process-pool utilities for Python callables |
| V8 | Async execution | Async task runner with bounded concurrency |
| V9 | Networking | TCP client/server and newline-delimited JSON protocol |
| V10 | REST API | FastAPI endpoints, validation, and API integration tests |
| V11 | Authentication | API-key authentication and protected API routes |
| V12 | Authorization and application security | Permission-oriented access control and security concepts |
| V13 | Scheduling | Recurring schedules, occurrences, and time-based job execution |
| V14 | Observability | Logging, correlation, metrics, health, and readiness concepts |
| V15 | Reliability and project hardening | Error handling, validation, resilience, and final engineering improvements |

The milestones represent the learning and implementation journey of the project. Passing automated tests verifies expected behavior but does not by itself make the platform production-ready.

---

# Project Structure

```text
forge/
├── src/
│   └── pyforge/
│       ├── domain/           # Core domain models and errors
│       ├── engine/           # Job execution and concurrency
│       ├── networking/       # TCP client, server, and protocol
│       ├── plugins/          # Executor plugin architecture
│       ├── scheduling/       # Scheduling and occurrence management
│       ├── storage/          # Repository implementations
│       ├── api.py            # FastAPI application
│       ├── cli.py            # Command-line interface
│       ├── manager.py        # Application orchestration
│       └── __main__.py       # Package entry point
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── examples/
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

The exact project structure may evolve as the application develops.

---

# Getting Started

## Requirements

- Python 3.10 or later.
- pip.
- Git.

## Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd forge
```

## Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Install dependencies

```bash
python -m pip install fastapi "uvicorn[standard]" python-dotenv httpx pytest
```

If dependencies are declared in `pyproject.toml`, install the project in editable mode:

```bash
python -m pip install -e .
```

---

# Configuration

Create a local environment file:

```bash
cp .env.example .env
```

Configure the required values, including:

```text
PYFORGE_API_KEY=replace_with_a_secure_secret
```

Never commit a real `.env` file containing secrets.

---

# Running Tests

Run the complete test suite:

```bash
PYTHONPATH=src python -m pytest -v
```

Run selected test groups:

```bash
PYTHONPATH=src python -m pytest tests/unit/ -v
```

```bash
PYTHONPATH=src python -m pytest tests/integration/ -v
```

The project contains both unit and integration tests covering domain behavior, execution, persistence, concurrency, networking, API behavior, scheduling, and failure handling.

---

# Running the REST API

Ensure the required environment variables are configured.

Start the development server:

```bash
PYTHONPATH=src python -m uvicorn pyforge.api:app --reload
```

Useful endpoints include:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/health`

---

# Example API Workflow

## 1. Check service health

```bash
curl http://127.0.0.1:8000/health
```

## 2. Create a job

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "name": "hello",
    "command": [
      "python3",
      "-c",
      "print(\"Hello from PyForge\")"
    ],
    "timeout": 10
  }'
```

The API returns a job object containing a unique job ID.

## 3. Execute the job

```bash
curl -X POST \
  "http://127.0.0.1:8000/jobs/YOUR_JOB_ID/run" \
  -H "X-API-Key: YOUR_API_KEY"
```

## 4. Retrieve the result

```bash
curl \
  -H "X-API-Key: YOUR_API_KEY" \
  http://127.0.0.1:8000/jobs/YOUR_JOB_ID/result
```

The result contains information about the execution, including output, errors, and execution status.

---

# Command-Line Interface

Run the CLI from the project root:

```bash
PYTHONPATH=src python -m pyforge --help
```

The CLI provides commands for managing jobs and inspecting execution behavior.

Use the help output to see the commands and arguments available in your installed version.

---

# Security Notes

PyForge is capable of executing operating-system commands.

Keep the following considerations in mind:

- Do not expose the service publicly without additional security controls.
- Keep secrets out of version control.
- Use environment variables for API keys and configuration.
- Treat external executor plugins as trusted code.
- Authentication alone does not provide process isolation or resource limits.
- Production deployment would require additional sandboxing and operational controls.

---

# What I Learned

PyForge was built as a practical systems and backend engineering project.

The project explores how the following concepts connect:

```text
Python
   |
   +-- Object-oriented design
   +-- Type hints
   +-- Exceptions
   +-- Dataclasses
   +-- Testing
   |
Operating Systems
   |
   +-- Processes
   +-- subprocess
   +-- stdout / stderr
   +-- Exit codes
   +-- Timeouts
   |
Concurrency
   |
   +-- Threads
   +-- Processes
   +-- asyncio
   |
Networking
   |
   +-- TCP
   +-- Client/server communication
   +-- Message framing
   +-- Protocol validation
   |
Backend Engineering
   |
   +-- REST APIs
   +-- Authentication
   +-- Authorization
   +-- Persistence
   +-- Scheduling
   +-- Observability
```

The goal of PyForge was not simply to use frameworks, but to understand how these components interact inside a backend system.

---

# Future Improvements

Potential future work includes:

- Containerized deployment.
- CI/CD pipelines.
- Process sandboxing and resource limits.
- Distributed workers.
- More executor implementations.
- Production-grade authentication.
- Advanced scheduling policies.
- External metrics backends.
- Web-based dashboard.

---

# Development Philosophy

PyForge was developed incrementally.

Each version introduced a concrete engineering capability, followed by testing and debugging before moving to the next layer.

The project demonstrates a progression from:

```text
Python fundamentals
        ↓
Command execution
        ↓
Persistence
        ↓
Architecture
        ↓
Concurrency
        ↓
Networking
        ↓
REST APIs
        ↓
Security
        ↓
Scheduling
        ↓
Observability
        ↓
Reliability
```

The objective is to understand not only how to write code, but how software components, operating systems, networks, storage, APIs, and application architecture work together.