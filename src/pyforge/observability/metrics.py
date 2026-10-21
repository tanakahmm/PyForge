from collections import Counter, defaultdict
from threading import Lock


class MetricsRegistry:
    """Thread-safe application metrics for PyForge."""

    def __init__(self) -> None:
        self._lock = Lock()

        self._request_counts: Counter[tuple[str, int]] = Counter()
        self._request_durations = defaultdict(
            lambda: [0, 0.0, 0.0]
        )

        self._job_counts: Counter[str] = Counter()
        self._job_durations = defaultdict(
            lambda: [0, 0.0, 0.0]
        )

    @staticmethod
    def _record_duration(
        collection: dict,
        key: tuple,
        duration: float,
    ) -> None:
        values = collection[key]
        values[0] += 1
        values[1] += duration
        values[2] = max(values[2], duration)

    def record_request(
        self,
        method: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        with self._lock:
            self._request_counts[(method, status_code)] += 1
            self._record_duration(
                self._request_durations,
                (method,),
                duration_seconds,
            )

    def record_job(
        self,
        status: str,
        duration_seconds: float,
    ) -> None:
        with self._lock:
            self._job_counts[status] += 1
            self._record_duration(
                self._job_durations,
                (status,),
                duration_seconds,
            )

    def render_prometheus(self) -> str:
        """Return metrics in Prometheus exposition format."""
        lines: list[str] = []

        with self._lock:
            lines.extend([
                "# HELP pyforge_http_requests_total Total HTTP requests",
                "# TYPE pyforge_http_requests_total counter",
            ])

            for (method, status), count in sorted(
                self._request_counts.items()
            ):
                lines.append(
                    f'pyforge_http_requests_total{{method="{method}",'
                    f'status="{status}"}} {count}'
                )

            lines.extend([
                "# HELP pyforge_http_request_duration_seconds "
                "HTTP request duration summary",
                "# TYPE pyforge_http_request_duration_seconds summary",
            ])

            for (method,), values in sorted(
                self._request_durations.items()
            ):
                count, total, maximum = values
                lines.extend([
                    f'pyforge_http_request_duration_seconds_count'
                    f'{{method="{method}"}} {count}',
                    f'pyforge_http_request_duration_seconds_sum'
                    f'{{method="{method}"}} {total}',
                    f'pyforge_http_request_duration_seconds_max'
                    f'{{method="{method}"}} {maximum}',
                ])

            lines.extend([
                "# HELP pyforge_jobs_completed_total "
                "Job execution outcomes",
                "# TYPE pyforge_jobs_completed_total counter",
            ])

            for status, count in sorted(self._job_counts.items()):
                lines.append(
                    f'pyforge_jobs_completed_total{{status="{status}"}} '
                    f"{count}"
                )

            lines.extend([
                "# HELP pyforge_job_duration_seconds "
                "Job execution duration summary",
                "# TYPE pyforge_job_duration_seconds summary",
            ])

            for (status,), values in sorted(
                self._job_durations.items()
            ):
                count, total, maximum = values
                lines.extend([
                    f'pyforge_job_duration_seconds_count'
                    f'{{status="{status}"}} {count}',
                    f'pyforge_job_duration_seconds_sum'
                    f'{{status="{status}"}} {total}',
                    f'pyforge_job_duration_seconds_max'
                    f'{{status="{status}"}} {maximum}',
                ])

        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()