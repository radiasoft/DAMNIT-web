import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DAMNIT_API_PERF_TEST"),
    reason="set DAMNIT_API_PERF_TEST to run",
)


def test_perf_generate():
    import sqlite3

    p = _proposal_dir()
    assert len(list(p.joinpath("extracted_data").glob("*.h5"))) == dev.LARGE_NUM_RUNS
    c = sqlite3.connect(p.joinpath(dev.DB_PATH))
    assert (
        c.execute("SELECT count(*) FROM run_info").fetchone()[0] == dev.LARGE_NUM_RUNS
    )
    c.close()


def test_perf_server():
    import httpx
    from pykern.pkunit import pkeq
    from damnit_api import unit_util

    with unit_util.server(_proposal_dir()) as url:
        pkeq(200, httpx.get(f"{url}/graphql", follow_redirects=True).status_code)


def _proposal_dir():
    from damnit_api.pkcli import dev
    from pykern import pkunit
    import pathlib

    d = pathlib.Path(pkunit.empty_work_dir())
    c = pkunit.data_dir().joinpath("cache", str(dev.LARGE_PROPOSAL))
    p = d.joinpath(str(dev.LARGE_PROPOSAL))
    if c.exists():
        p.symlink_to(c)
    else:
        dev.setup_perf_test(str(d))
    return p
