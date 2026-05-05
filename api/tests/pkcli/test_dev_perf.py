import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DAMNIT_API_PERF_TEST"),
    reason="set DAMNIT_API_PERF_TEST to run",
)

_EXTRACTED_QUERY = """
query ExtractedDataQuery($proposal: String, $run: Int!, $variable: String!) {
  extracted_data(database: { proposal: $proposal }, run: $run, variable: $variable)
}
"""

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


def test_perf_large_image():
    """Compare GraphQL (RGBA+base64+JSON) vs pykern.api (RGBA+binary+msgpack) for 10 concurrent large_image requests."""
    import asyncio
    import time
    from pykern.api import client
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    proposal = str(dev._SETUP_TEST.large.proposal)
    runs = list(range(1, 11))
    v = "large_image"

    async def _pykern(cfg):
        async with client.Client(cfg) as c:
            t = time.time()
            await asyncio.gather(
                *[
                    c.call_api(
                        "image_data", PKDict(proposal=proposal, run=r, variable=v)
                    )
                    for r in runs
                ]
            )
            pkdlog(
                "pykern large_image (rgba+binary+msgpack): {:.3f}s  requests={}",
                time.time() - t,
                len(runs),
            )

    p = _proposal_dir("large")
    with unit_util.server(p) as url:
        asyncio.run(
            _gql_extracted(
                url, proposal, runs, [v], "graphql large_image (rgba+base64+json)"
            )
        )
    with unit_util.pykern_api_server(path=p) as cfg:
        asyncio.run(_pykern(cfg))


def test_perf_pykern_api():
    import asyncio
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    proposal = str(dev._SETUP_TEST.large.proposal)
    per_page = 10

    p = _proposal_dir("large")
    with unit_util.server(p) as url:
        m = asyncio.run(_gql_metadata(url, proposal))
    with unit_util.pykern_api_server(path=p) as cfg:
        asyncio.run(
            _pykern_extracted(
                cfg,
                proposal,
                m["runs"][:per_page],
                [n for n in m["variables"] if n not in ("run", "proposal")],
                "pykern extracted_data",
            )
        )


def test_perf_server():
    import asyncio
    import time
    import httpx
    from pykern.pkdebug import pkdlog
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    proposal = str(dev._SETUP_TEST.large.proposal)

    async def _runs(url, num_runs, per_page=10):
        async with httpx.AsyncClient(base_url=url, timeout=120.0) as c:
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

    async def _run(url):
        m = await _gql_metadata(url, proposal)
        pkdlog(
            "metadata: variables={}  runs={}",
            len(m["variables"]),
            len(m["runs"]),
        )
        await _runs(url, len(m["runs"]))
        await _gql_extracted(
            url,
            proposal,
            m["runs"],
            [n for n in m["variables"] if n not in ("run", "proposal")],
            "extracted_data",
        )

    with unit_util.server(_proposal_dir("large")) as url:
        asyncio.run(_run(url))


def test_perf_wide_table():
    """Compare GraphQL vs pykern.api for 10 runs x 10 small (256x256) images."""
    import asyncio
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    proposal = str(dev._SETUP_TEST.wide.proposal)
    per_page = 10

    p = _proposal_dir("wide")
    with unit_util.server(p) as url:
        m = asyncio.run(_gql_metadata(url, proposal))
        run_ids = m["runs"][:per_page]
        variables = [f"image_{i:02d}" for i in range(10)]
        asyncio.run(
            _gql_extracted(url, proposal, run_ids, variables, "graphql wide_table")
        )
    with unit_util.pykern_api_server(path=p) as cfg:
        asyncio.run(
            _pykern_extracted(cfg, proposal, run_ids, variables, "pykern wide_table")
        )


async def _gql_extracted(url, proposal, run_ids, variables, label):
    import asyncio
    import time
    import httpx
    from pykern.pkdebug import pkdlog

    async with httpx.AsyncClient(base_url=url, timeout=120.0) as c:
        t = time.time()
        tasks = [
            c.post(
                "/graphql",
                json={
                    "query": _EXTRACTED_QUERY,
                    "variables": {"proposal": proposal, "run": r, "variable": v},
                },
            )
            for r in run_ids
            for v in variables
        ]
        results = await asyncio.gather(*tasks)
        for r in results:
            r.raise_for_status()
        pkdlog("{}: {:.3f}s  requests={}", label, time.time() - t, len(tasks))


async def _gql_metadata(url, proposal):
    import httpx

    async with httpx.AsyncClient(base_url=url, timeout=30.0) as c:
        r = await c.post(
            "/graphql",
            json={"query": _METADATA_QUERY, "variables": {"proposal": proposal}},
        )
        return r.json()["data"]["metadata"]


def _proposal_dir(kind):
    from damnit_api.pkcli import dev
    from pykern import pkunit
    import pathlib

    cache = pathlib.Path(pkunit.data_dir()).joinpath("cache")
    work = pathlib.Path(pkunit.empty_work_dir())
    proposal = str(dev._SETUP_TEST[kind].proposal)
    link = work.joinpath(proposal)
    if not cache.joinpath(proposal).exists():
        dev.setup_test(kind, str(cache))
    link.symlink_to(cache.joinpath(proposal))
    return work


async def _pykern_extracted(cfg, proposal, run_ids, variables, label):
    import asyncio
    import time
    from pykern.api import client
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog

    async with client.Client(cfg) as c:
        t = time.time()
        tasks = [
            c.call_api("extracted_data", PKDict(proposal=proposal, run=r, variable=v))
            for r in run_ids
            for v in variables
        ]
        await asyncio.gather(*tasks)
        pkdlog("{}: {:.3f}s  requests={}", label, time.time() - t, len(tasks))
