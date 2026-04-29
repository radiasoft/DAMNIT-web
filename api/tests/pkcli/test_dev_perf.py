import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DAMNIT_API_PERF_TEST"),
    reason="set DAMNIT_API_PERF_TEST to run",
)

_METADATA_QUERY = """
query TableMetadataQuery($proposal: String) {
  metadata(database: { proposal: $proposal })
}
"""

_RUNS_QUERY = """
query GetTableData($proposal: String, $page: Int, $per_page: Int) {
  runs(database: { proposal: $proposal }, page: $page, per_page: $per_page) {
    variables {
      name
      value
      dtype
    }
  }
}
"""

_EXTRACTED_QUERY = """
query ExtractedDataQuery($proposal: String, $run: Int!, $variable: String!) {
  extracted_data(database: { proposal: $proposal }, run: $run, variable: $variable)
}
"""


def test_perf_generate():
    import sqlite3
    from damnit_api.pkcli import dev

    p = _proposal_dir()
    assert len(list(p.joinpath("extracted_data").glob("*.h5"))) == dev.LARGE_NUM_RUNS
    c = sqlite3.connect(p.joinpath(dev.DB_PATH))
    assert (
        c.execute("SELECT count(*) FROM run_info").fetchone()[0] == dev.LARGE_NUM_RUNS
    )
    c.close()


def test_perf_server():
    import asyncio
    import time
    import httpx
    from pykern.pkdebug import pkdlog
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    proposal = str(dev.LARGE_PROPOSAL)

    async def _metadata(c):
        t = time.time()
        r = await c.post(
            "/graphql",
            json={"query": _METADATA_QUERY, "variables": {"proposal": proposal}},
        )
        m = r.json()["data"]["metadata"]
        pkdlog(
            "metadata: {:.3f}s  variables={}  runs={}",
            time.time() - t,
            len(m["variables"]),
            len(m["runs"]),
        )
        return m

    async def _runs(c, num_runs, per_page=10):
        t = time.time()
        pages = (num_runs + per_page - 1) // per_page
        for page in range(1, pages + 1):
            r = await c.post(
                "/graphql",
                json={
                    "query": _RUNS_QUERY,
                    "variables": {
                        "proposal": proposal,
                        "page": page,
                        "per_page": per_page,
                    },
                },
            )
            r.raise_for_status()
        pkdlog(
            "runs: {:.3f}s  pages={}  per_page={}",
            time.time() - t,
            pages,
            per_page,
        )

    async def _extracted(c, run_ids, variables, per_page=10):
        t = time.time()
        r = run_ids[:per_page]
        tasks = [
            c.post(
                "/graphql",
                json={
                    "query": _EXTRACTED_QUERY,
                    "variables": {
                        "proposal": proposal,
                        "run": int(run),
                        "variable": v,
                    },
                },
            )
            for run in r
            for v in variables
        ]
        results = await asyncio.gather(*tasks)
        for r in results:
            r.raise_for_status()
        pkdlog(
            "extracted_data: {:.3f}s  requests={}",
            time.time() - t,
            len(tasks),
        )

    async def _run(url):
        async with httpx.AsyncClient(base_url=url, timeout=120.0) as c:
            m = await _metadata(c)
            await _runs(c, len(m["runs"]))
            variables = [n for n in m["variables"] if n not in ("run", "proposal")]
            await _extracted(c, m["runs"], variables)

    with unit_util.server(_proposal_dir()) as url:
        asyncio.run(_run(url))


def test_perf_pykern_api():
    import asyncio
    import time
    from pykern.api import client
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    per_page = 10
    run_ids = list(range(1, per_page + 1))
    variables = list(dev._PERF_VARIABLES.keys())

    async def _extracted(c):
        t = time.time()
        tasks = [
            c.call_api("extracted_data", PKDict(run=run, variable=v))
            for run in run_ids
            for v in variables
        ]
        results = await asyncio.gather(*tasks)
        pkdlog(
            "pykern extracted_data: {:.3f}s  requests={}",
            time.time() - t,
            len(tasks),
        )
        return results

    async def _run(cfg):
        async with client.Client(cfg) as c:
            await _extracted(c)

    p = _proposal_dir()
    with unit_util.pykern_api_server(path=p) as cfg:
        asyncio.run(_run(cfg))


def _proposal_dir():
    from damnit_api.pkcli import dev
    from pykern import pkunit
    import pathlib

    d = pathlib.Path(pkunit.empty_work_dir())
    c = pathlib.Path(pkunit.data_dir()).joinpath("cache", str(dev.LARGE_PROPOSAL))
    p = d.joinpath(str(dev.LARGE_PROPOSAL))
    if c.exists():
        p.symlink_to(c)
    else:
        dev.setup_perf_test(str(d))
    return p
