import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DAMNIT_API_PERF_TEST"),
    reason="set DAMNIT_API_PERF_TEST to run",
)

_PER_PAGE = 10

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


def test_large_image():
    """Compare GraphQL (RGBA+base64+JSON) vs pykern.api (RGBA+binary+msgpack) for 10 concurrent large_image requests."""
    import asyncio
    import time
    from pykern.api import client
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    proposal = str(dev._SETUP_TEST.large.proposal)
    runs = list(range(1, 51))
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


def test_server():
    """Compare GraphQL vs pykern.api: page through all runs fetching extracted data."""
    import asyncio
    import time
    import httpx
    from pykern.pkdebug import pkdlog
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    p = _proposal_dir("large")
    proposal = str(dev._SETUP_TEST.large.proposal)

    async def _graphql(url):
        m = await _gql_metadata(url, proposal)
        runs = m["runs"]
        variables = [n for n in m["variables"] if n not in ("run", "proposal")]
        pkdlog("metadata: variables={}  runs={}", len(variables), len(runs))
        t = time.time()
        pages = (len(runs) + _PER_PAGE - 1) // _PER_PAGE
        async with httpx.AsyncClient(base_url=url, timeout=120.0) as c:
            for page in range(1, pages + 1):
                (
                    await c.post(
                        "/graphql",
                        json={
                            "query": _RUNS_QUERY,
                            "variables": {
                                "proposal": proposal,
                                "page": page,
                                "per_page": _PER_PAGE,
                            },
                        },
                    )
                ).raise_for_status()
                page_runs = runs[(page - 1) * _PER_PAGE : page * _PER_PAGE]
                await _gql_extracted(
                    url, proposal, page_runs, variables, f"graphql page {page}"
                )
        pkdlog("graphql total: {:.3f}s  pages={}", time.time() - t, pages)
        return runs, variables

    with unit_util.server(p) as url:
        runs, variables = asyncio.run(_graphql(url))
    with unit_util.pykern_api_server(path=p) as cfg:
        asyncio.run(_pykern_extracted(cfg, proposal, runs, variables, "pykern server"))


def test_wide_table():
    """Compare GraphQL vs pykern.api for 10 runs x 10 small (256x256) images."""
    import asyncio
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    proposal = str(dev._SETUP_TEST.wide.proposal)

    p = _proposal_dir("wide")
    with unit_util.server(p) as url:
        m = asyncio.run(_gql_metadata(url, proposal))
        run_ids = m["runs"][:_PER_PAGE]
        variables = [f"image_{i:02d}" for i in range(10)]
        asyncio.run(
            _gql_extracted(url, proposal, run_ids, variables, "graphql wide_table")
        )
    with unit_util.pykern_api_server(path=p) as cfg:
        asyncio.run(
            _pykern_extracted(cfg, proposal, run_ids, variables, "pykern wide_table")
        )


async def _gql_extracted(url, proposal, run_ids, variables, label):
    import time
    import httpx
    from pykern.pkdebug import pkdlog

    async with httpx.AsyncClient(base_url=url, timeout=120.0) as c:
        t = time.time()
        n = 0
        for r in run_ids:
            for v in variables:
                (
                    await c.post(
                        "/graphql",
                        json={
                            "query": _EXTRACTED_QUERY,
                            "variables": {
                                "proposal": proposal,
                                "run": r,
                                "variable": v,
                            },
                        },
                    )
                ).raise_for_status()
                n += 1
        pkdlog("{}: {:.3f}s  requests={}", label, time.time() - t, n)


async def _gql_metadata(url, proposal):
    import httpx

    async with httpx.AsyncClient(base_url=url, timeout=30.0) as c:
        r = await c.post(
            "/graphql",
            json={"query": _METADATA_QUERY, "variables": {"proposal": proposal}},
        )
        return r.json()["data"]["metadata"]


def _proposal_dir(kind):
    from damnit_api.db import _proposal_map
    from damnit_api.pkcli import dev
    from pykern import pkunit
    import pathlib

    c = pathlib.Path(pkunit.data_dir()).joinpath(
        "cache", str(dev._SETUP_TEST[kind].proposal)
    )
    if not c.exists():
        dev.setup_test(kind, c.parent)
    rv = pathlib.Path(pkunit.empty_work_dir())
    rv.joinpath(c.name).symlink_to(c)
    _proposal_map.cache_clear()
    return rv


async def _pykern_extracted(cfg, proposal, run_ids, variables, label):
    import time
    from pykern.api import client
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog

    async with client.Client(cfg) as c:
        t = time.time()
        n = 0
        for r in run_ids:
            for v in variables:
                await c.call_api(
                    "extracted_data", PKDict(proposal=proposal, run=r, variable=v)
                )
                n += 1
        pkdlog("{}: {:.3f}s  requests={}", label, time.time() - t, n)
