from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import contextlib
import os
import pykern.pkconst
import pykern.util
import signal
import threading
import time


def uvicorn_server(path):
    """Start the uvicorn API server against ``path`` and yield the base URL."""

    port = pykern.util.unbound_localhost_tcp_port()

    def _child():
        import os
        import uvicorn

        os.environ["DW_API_DAMNIT_PATH"] = str(path)
        from damnit_api import main
        from damnit_api.shared import settings

        settings.settings = settings.Settings(damnit_path=path)
        c = uvicorn.Config(
            main.create_app(),
            host=pykern.pkconst.LOCALHOST_IP,
            port=port,
            log_level="error",
        )
        uvicorn.Server(c).run()

    return _server_start(f"http://{pykern.pkconst.LOCALHOST_IP}:{port}", _child)


def pykern_api_server(path):
    """Start a pykern.api Tornado server and yield its connection config."""
    from pykern.api import server
    from pykern.pkcollections import PKDict

    cfg = PKDict(
        api_uri="/api-v1",
        tcp_ip=pykern.pkconst.LOCALHOST_IP,
        tcp_port=pykern.util.unbound_localhost_tcp_port(),
    )

    def _child():
        if path is not None:
            os.environ["DW_API_DAMNIT_PATH"] = str(path)
            from pykern import pkconfig

            pkconfig.reset_state_for_testing(
                PKDict(DAMNIT_API_PROPOSAL_API_DAMNIT_PATH=str(path))
            )
        from damnit_api import proposal_api

        server.start(
            api_classes=[proposal_api.API],
            attr_classes=[],
            http_config=cfg.copy(),
        )

    return _server_start(cfg, _child)


@contextlib.contextmanager
def _server_start(result, child):
    pid = os.fork()
    if pid == 0:
        try:
            child()
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())
        finally:
            os._exit(0)
    time.sleep(1)
    try:
        yield result
    finally:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
