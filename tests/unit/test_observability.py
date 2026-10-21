from pyforge.observability.metrics import MetricsRegistry


def test_request_metrics_are_recorded():
    registry = MetricsRegistry()

    registry.record_request("GET", 200, 0.1)
    registry.record_request("GET", 200, 0.2)
    registry.record_request("POST", 500, 0.4)

    output = registry.render_prometheus()

    assert 'method="GET",status="200"} 2' in output
    assert 'method="POST",status="500"} 1' in output
    assert "pyforge_http_request_duration_seconds_count" in output


def test_job_outcomes_and_durations_are_recorded():
    registry = MetricsRegistry()

    registry.record_job("success", 0.25)
    registry.record_job("success", 0.75)
    registry.record_job("failed", 1.0)

    output = registry.render_prometheus()

    assert 'status="success"} 2' in output
    assert 'status="failed"} 1' in output
    assert "pyforge_job_duration_seconds_sum" in output