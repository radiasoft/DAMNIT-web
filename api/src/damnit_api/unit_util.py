from pykern.pkdebug import pkdc, pkdlog, pkdp
import contextlib
import os
import pykern.pkconst
import pykern.util
import signal
import threading
import time


@contextlib.contextmanager
def server(path):
    """Start the API server against ``path`` and yield the base URL."""

    def _start():
        import os
        import uvicorn
        os.environ["DW_API_DAMNIT_PATH"] = str(path)
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


@contextlib.contextmanager
def pykern_api_server(path=None):
    """Start a pykern.api Tornado server and yield its connection config."""
    from pykern.api import server as _server
    from pykern.pkcollections import PKDict

    p = pykern.util.unbound_localhost_tcp_port()
    cfg = PKDict(
        api_uri="/api-v1",
        tcp_ip=pykern.pkconst.LOCALHOST_IP,
        tcp_port=p,
    )
    pid = os.fork()
    if pid == 0:
        try:
            if path is not None:
                from pykern import pkconfig as _pkconfig
                _pkconfig.reset_state_for_testing(
                    PKDict(DAMNIT_API_QUEST_API_DAMNIT_PATH=str(path))
                )
            from damnit_api import quest_api
            _server.start(
                api_classes=[quest_api.API],
                attr_classes=[],
                http_config=cfg.copy(),
            )
        except Exception as e:
            pkdlog("exception={} stack={}", e)
        finally:
            os._exit(0)
    time.sleep(1)
    try:
        yield cfg
    finally:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
