from pykern.pkdebug import pkdc, pkdlog, pkdp
import contextlib
import pykern.pkconst
import pykern.util
import threading
import time


@contextlib.contextmanager
def server(path):
    """Start the API server against ``path`` and yield the base URL."""

    def _start():
        import uvicorn
        from damnit_api import main
        from damnit_api.shared import settings

        settings.settings = settings.Settings(damnit_path=path)
        c = uvicorn.Config(
            main.create_app(),
            host=pykern.pkconst.LOCALHOST_IP,
            port=p,
            log_level="error",
        )
        v = uvicorn.Server(c)
        threading.Thread(target=v.run, daemon=True).start()
        while not v.started:
            time.sleep(0.05)
        return v

    p = pykern.util.unbound_localhost_tcp_port()
    v = _start()
    try:
        yield f"http://{pykern.pkconst.LOCALHOST_IP}:{p}"
    finally:
        v.should_exit = True
