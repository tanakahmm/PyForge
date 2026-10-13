import argparse
import json
import sqlite3
import sys

from pyforge.engine.manager import JobManager
from pyforge.engine.sync_executor import SyncExecutor
from pyforge.exceptions import PyForgeError
from pyforge.storage.sqlite_repository import SQLiteRepository
from pyforge.plugins import create_default_registry


def build_parser() -> argparse.ArgumentParser:
    """Define the commands and arguments accepted by PyForge."""

    parser = argparse.ArgumentParser(
        prog="pyforge",
        description="A Python job execution and automation platform.",
    )

    parser.add_argument(
        "--db",
        default="pyforge.db",
        help="Path to the SQLite database (default: pyforge.db).",
    )

    commands = parser.add_subparsers(
        dest="action",
        required=True,
    )

    # pyforge create --name backup -- echo hello
    create = commands.add_parser(
        "create",
        help="Create a job.",
    )
    create.add_argument("--name", required=True)
    create.add_argument("--timeout", type=float, default=30.0)
    create.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Metadata entry; may be supplied multiple times.",
    )
    create.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="OS command to execute; place it after --.",
    )

    commands.add_parser("list", help="List all jobs.")

    show = commands.add_parser("show", help="Show a job.")
    show.add_argument("job_id")

    run = commands.add_parser("run", help="Execute a job.")
    run.add_argument("job_id")
    run.add_argument(
    "--executor",
    default="sync",
    help="Name of the executor plugin to use (default: sync).",)

    run_many = commands.add_parser(
        "run-many",
        help="Execute multiple jobs concurrently.",
    )
    run_many.add_argument(
        "job_ids",
        nargs="+",
        help="One or more saved job IDs.",
    )
    run_many.add_argument(
        "--executor",
        default="sync",
        help="Executor plugin name (default: sync).",
    )
    run_many.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum number of concurrent worker threads.",
    )

    result = commands.add_parser(
        "result",
        help="Show an execution result.",
    )
    result.add_argument("job_id")

    delete = commands.add_parser(
        "delete",
        help="Delete a job and its result.",
    )
    delete.add_argument("job_id")

    return parser


def _parse_metadata(
    entries: list[str],
    parser: argparse.ArgumentParser,
) -> dict[str, str]:
    """Convert KEY=VALUE arguments into a dictionary."""

    metadata: dict[str, str] = {}

    for entry in entries:
        if "=" not in entry:
            parser.error(
                f"Invalid metadata {entry!r}; expected KEY=VALUE."
            )

        key, value = entry.split("=", 1)

        if not key:
            parser.error("Metadata keys cannot be empty.")

        metadata[key] = value

    return metadata


def _print_json(value: object) -> None:
    """Print a JSON-serializable value in a readable format."""

    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    """Run the PyForge CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        repository = SQLiteRepository(args.db)
        manager = JobManager(repository=repository)

        if args.action == "create":
            command = list(args.command)

            # argparse may retain the -- separator in REMAINDER.
            if command and command[0] == "--":
                command = command[1:]

            if not command:
                parser.error(
                    "A command is required after --. "
                    "Example: create --name demo -- echo hello"
                )

            if args.timeout <= 0:
                parser.error("--timeout must be greater than zero.")

            metadata = _parse_metadata(args.metadata, parser)

            job = manager.create_job(
                name=args.name,
                command=command,
                timeout=args.timeout,
                metadata=metadata,
            )

            _print_json({
                "message": "Job created",
                "job_id": job.id,
                "name": job.name,
                "command": job.command,
                "status": job.status.value,
            })
            return 0

        if args.action == "list":
            jobs = manager.list_jobs()

            _print_json([
                {
                    "id": job.id,
                    "name": job.name,
                    "command": job.command,
                    "status": job.status.value,
                    "created_at": job.created_at.isoformat(),
                }
                for job in jobs
            ])
            return 0

        if args.action == "show":
            job = manager.get_job(args.job_id)

            _print_json({
                "id": job.id,
                "name": job.name,
                "command": job.command,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "timeout": job.timeout,
                "metadata": job.metadata,
            })
            return 0

        if args.action == "run":
            registry = create_default_registry()
            executor = registry.create_executor(args.executor)
            result = manager.execute_job(
                args.job_id,
                executor,
            )

            _print_json({
                "job_id": result.job_id,
                "status": result.status.value,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "started_at": result.started_at.isoformat(),
                "finished_at": result.finished_at.isoformat(),
                "error": result.error,
            })

            # Preserve the executed command's exit status when valid.
            if 0 <= result.exit_code <= 255:
                return result.exit_code

            return 1

        if args.action == "run-many":
            if args.max_workers < 1:
                parser.error("--max-workers must be at least 1")

            if len(set(args.job_ids)) != len(args.job_ids):
                parser.error("Duplicate job IDs are not allowed")

            registry = create_default_registry()
            results = manager.execute_jobs_concurrently(
                args.job_ids,
                executor_factory=lambda: registry.create_executor(
                    args.executor
                ),
                max_workers=args.max_workers,
            )

            _print_json([
                {
                    "job_id": result.job_id,
                    "status": result.status.value,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "error": result.error,
                }
                for result in results
            ])

            return 0 if all(
                result.status.value == "success"
                for result in results
            ) else 1

        if args.action == "result":
            result = manager.get_result(args.job_id)

            _print_json({
                "job_id": result.job_id,
                "status": result.status.value,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "started_at": result.started_at.isoformat(),
                "finished_at": result.finished_at.isoformat(),
                "error": result.error,
            })
            return 0

        if args.action == "delete":
            manager.remove_job(args.job_id)
            print(f"Deleted job {args.job_id}")
            return 0

        parser.error(f"Unsupported action: {args.action}")

    except PyForgeError as exc:
        print(f"PyForge error: {exc}", file=sys.stderr)
        return 1

    except sqlite3.Error as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
