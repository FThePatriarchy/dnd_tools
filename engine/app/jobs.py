"""Background jobs for the web app: run an operation in a thread, keep its log and result for the page to poll."""
from dataclasses import dataclass, field
import itertools
import threading
import time
import traceback

MAX_JOBS = 50  # finished jobs kept for the page; the oldest are dropped


@dataclass
class Job:
    id: int
    kind: str
    request: dict
    status: str = "running"            # running, done, failed
    log: list = field(default_factory=list)
    result: object = None
    error: str = ""
    started: float = field(default_factory=time.time)
    finished: float | None = None

    def view(self, since=0):
        return {"id": self.id, "kind": self.kind, "status": self.status, "log": self.log[since:], "log_size": len(self.log),
                "result": self.result if self.status == "done" else None, "error": self.error,
                "elapsed": (self.finished or time.time()) - self.started}


class Jobs:
    def __init__(self, operations):
        self.operations = operations   # kind -> function(request, log)
        self.jobs = {}
        self.lock = threading.Lock()
        self.ids = itertools.count(1)

    def start(self, kind, request):
        if kind not in self.operations: raise ValueError(f"unknown job kind {kind!r}")
        job = Job(next(self.ids), kind, request)
        with self.lock:
            self.jobs[job.id] = job
            for old in sorted(self.jobs)[:-MAX_JOBS]:
                if self.jobs[old].status != "running": del self.jobs[old]
        threading.Thread(target=self._run, args=(job,), daemon=True, name=f"job-{job.id}").start()
        return job

    def _run(self, job):
        def log(message):
            job.log.append({"t": round(time.time() - job.started, 1), "message": str(message)})
        try:
            job.result = self.operations[job.kind](job.request, log)
            job.status = "done"
        except ValueError as exc:
            job.error, job.status = str(exc), "failed"
        except Exception as exc:  # an engine bug: keep the trace for the report
            job.error, job.status = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}", "failed"
        finally:
            job.finished = time.time()

    def get(self, job_id):
        with self.lock: return self.jobs.get(job_id)

    def list(self):
        with self.lock:
            return [{"id": j.id, "kind": j.kind, "status": j.status, "elapsed": (j.finished or time.time()) - j.started}
                    for j in sorted(self.jobs.values(), key=lambda j: -j.id)]
