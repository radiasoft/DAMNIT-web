import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DAMNIT_API_PERF_TEST"),
    reason="set DAMNIT_API_PERF_TEST to run",
)

_PER_PAGE = 10

_DEFERRED_QUERY = """
query DeferredTableDataQuery($proposal: String, $page: Int, $per_page: Int, $names: [String!]) {
  runs(database: { proposal: $proposal }, page: $page, per_page: $per_page) {
    variables(names: $names) {
      name
      value
      dtype
    }
  }
}
"""

_LIGHTWEIGHT_QUERY = """
query LightweightTableDataQuery($proposal: String, $page: Int, $per_page: Int) {
  runs(database: { proposal: $proposal }, page: $page, per_page: $per_page) @lightweight {
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

_METADATA_QUERY = """
query TableMetadataQuery($proposal: String) {
  metadata(database: { proposal: $proposal })
}
"""

_LARGE_IMAGE = "large_image"


def test_image_large():
    """Fetch a single large image N times via GraphQL deferred query."""
    import asyncio
    import time
    import httpx
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    def _args(kind):
        s = dev._SETUP_TEST.large
        return PKDict(proposal=str(s.proposal), runs=tuple(range(1, s.runs + 1)))

    async def _graphql(url, proposal, runs):
        async with httpx.AsyncClient(base_url=url, timeout=120.0) as c:
            t = time.time()
            for run in runs:
                (
                    await c.post(
                        "/graphql",
                        json={
                            "query": _EXTRACTED_QUERY,
                            "variables": {
                                "proposal": proposal,
                                "run": run,
                                "variable": _LARGE_IMAGE,
                            },
                        },
                    )
                ).raise_for_status()
            pkdlog(
                "graphql large_image: {:.3f}s  runs={}",
                time.time() - t,
                len(runs),
            )

    with unit_util.server(_proposal_dir("large")) as url:
        asyncio.run(_graphql(url, **_args("large")))


def test_table_large():
    """Lightweight+deferred table load: GraphQL (2 requests/page) vs pykern.api (1 request/page)."""
    _table("large")


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


def _table(kind):
    """Lightweight+deferred (GraphQL) vs single call (pykern.api) for one page of runs."""
    import asyncio
    import time
    import httpx
    from pykern.api import client
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    proposal = str(dev._SETUP_TEST[kind].proposal)

    async def _graphql(url):
        async with httpx.AsyncClient(base_url=url, timeout=120.0) as c:
            t = time.time()
            r = (
                await c.post(
                    "/graphql",
                    json={
                        "query": _LIGHTWEIGHT_QUERY,
                        "variables": {
                            "proposal": proposal,
                            "page": 1,
                            "per_page": _PER_PAGE,
                        },
                    },
                )
            ).raise_for_status()
            runs = r.json()["data"]["runs"]
            heavy = list(
                {
                    v["name"]
                    for run in runs
                    for v in run["variables"]
                    if v["value"] is None
                }
            )
            if heavy:
                (
                    await c.post(
                        "/graphql",
                        json={
                            "query": _DEFERRED_QUERY,
                            "variables": {
                                "proposal": proposal,
                                "page": 1,
                                "per_page": _PER_PAGE,
                                "names": heavy,
                            },
                        },
                    )
                ).raise_for_status()
            pkdlog(
                "graphql table: {:.3f}s  runs={}  heavy={}",
                time.time() - t,
                len(runs),
                len(heavy),
            )

    async def _pykern(cfg):
        t = time.time()
        async with client.Client(cfg) as c:
            r = await c.call_api(
                "table",
                PKDict(proposal=proposal, start_page=1, runs_per_page=_PER_PAGE),
            )
        pkdlog("pykern table: {:.3f}s  runs={}", time.time() - t, len(r.runs))

    p = _proposal_dir(kind)
    with unit_util.server(p) as url:
        asyncio.run(_graphql(url))
    with unit_util.pykern_api_server(path=p) as cfg:
        asyncio.run(_pykern(cfg))
