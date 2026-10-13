
import json
import sys

from pyforge.cli import main


def test_create_and_list_jobs(tmp_path, capsys):
    db_path = str(tmp_path / "cli.db")

    exit_code = main([
        "--db", db_path,
        "create",
        "--name", "demo",
        "--", "echo", "hello",
    ])

    assert exit_code == 0

    created = json.loads(capsys.readouterr().out)
    job_id = created["job_id"]

    exit_code = main(["--db", db_path, "list"])

    assert exit_code == 0
    jobs = json.loads(capsys.readouterr().out)

    assert len(jobs) == 1
    assert jobs[0]["id"] == job_id
    assert jobs[0]["name"] == "demo"


def test_run_and_retrieve_result(tmp_path, capsys):
    db_path = str(tmp_path / "cli.db")

    exit_code = main([
        "--db", db_path,
        "create",
        "--name", "python-demo",
        "--",
        sys.executable,
        "-c",
        "print('hello from PyForge')",
    ])

    assert exit_code == 0
    job_id = json.loads(capsys.readouterr().out)["job_id"]

    exit_code = main(["--db", db_path, "run", job_id])

    assert exit_code == 0
    run_output = json.loads(capsys.readouterr().out)
    assert run_output["status"] == "success"
    assert "hello from PyForge" in run_output["stdout"]

    exit_code = main(["--db", db_path, "result", job_id])

    assert exit_code == 0
    saved_result = json.loads(capsys.readouterr().out)
    assert saved_result["job_id"] == job_id
    assert saved_result["status"] == "success"


def test_delete_job(tmp_path, capsys):
    db_path = str(tmp_path / "cli.db")

    main([
        "--db", db_path,
        "create",
        "--name", "temporary",
        "--", "echo", "temporary",
    ])

    job_id = json.loads(capsys.readouterr().out)["job_id"]

    exit_code = main(["--db", db_path, "delete", job_id])

    assert exit_code == 0
    assert f"Deleted job {job_id}" in capsys.readouterr().out

    # The job should no longer exist.
    exit_code = main(["--db", db_path, "show", job_id])

    assert exit_code == 1
    assert "was not found" in capsys.readouterr().err
