from damnit_api.pkcli import dev
from pykern.pkdebug import pkdc, pkdlog, pkdp
import damnit_api.unit_util
import httpx
import os
import pathlib
import pykern.pkunit
import pytest
import sqlite3

pytestmark = pytest.mark.skipif(
    not os.environ.get("DAMNIT_API_PERF_TEST"),
    reason="set DAMNIT_API_PERF_TEST to run",
)


def test_perf_generate():
    d = pathlib.Path(pykern.pkunit.empty_work_dir())
    dev.setup_perf_test(str(d))
    p = d.joinpath(str(dev.LARGE_PROPOSAL))
    assert len(list(p.joinpath("extracted_data").glob("*.h5"))) == dev.LARGE_NUM_RUNS
    c = sqlite3.connect(p.joinpath(dev.DB_PATH))
    assert (
        c.execute("SELECT count(*) FROM run_info").fetchone()[0] == dev.LARGE_NUM_RUNS
    )
    c.close()


def test_perf_server():
    from pykern.pkunit import pkeq

    d = pathlib.Path(pykern.pkunit.empty_work_dir())
    dev.setup_perf_test(str(d))
    p = d.joinpath(str(dev.LARGE_PROPOSAL))
    with damnit_api.unit_util.server(p) as url:
        pkeq(200, httpx.get(f"{url}/graphql", follow_redirects=True).status_code)
