import asyncio
import os
import signal
import threading
import time
from typing import Any

from uvicorn.workers import UvicornWorker


# This file is here to make sure our application automatically reloads when
# the python files it's serving have changed. This is *supposed* to be handled
# automatically by gunicorn, but there's a bug in the interaction between
# gunicorn (our web process manager) and uvicorn (our application server) that
# we're working around for now.
# Code from https://github.com/encode/uvicorn/pull/1193/files
class ReloaderThread(threading.Thread):
    def __init__(self, worker: "ReloadingWorker", sleep_interval: float = 1.0):
        super().__init__()
        self.setDaemon(True)
        self._worker = worker
        self._interval = sleep_interval

    def run(self) -> None:
        while True:
            if not self._worker.alive:
                os.kill(os.getpid(), signal.SIGINT)
            time.sleep(self._interval)


class ReloadingWorker(UvicornWorker):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._reloader_thread = ReloaderThread(self)

    def run(self) -> None:
        if self.cfg.reload:
            self._reloader_thread.start()

        return asyncio.run(self._serve())
