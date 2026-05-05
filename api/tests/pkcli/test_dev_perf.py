import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DAMNIT_API_PERF_TEST"),
    reason="set DAMNIT_API_PERF_TEST to run",
)

_PER_PAGE = 10

_MAX_PAGES = 100

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
    """Lightweight+deferred table load: GraphQL (2 requests/page) vs pykern.api (1 request/page)."""
    import asyncio
    import time
    import httpx
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    def _dump_msg(obj, base):
        if False:
            pkjson.dump_pretty(obj, filename=pkunit.work_dir().joinpath(f"{base}.json"))

    proposal = str(dev._SETUP_TEST[kind].proposal)

    async def _graphql(url):

        async with httpx.AsyncClient(base_url=url, timeout=120.0) as c:
            m = (
                (
                    await c.post(
                        "/graphql",
                        json={
                            "query": _METADATA_QUERY,
                            "variables": {"proposal": proposal},
                        },
                    )
                )
                .raise_for_status()
                .json()["data"]["metadata"]
            )
            _dump_msg(m, "metadata")
            pkdlog(
                "metadata: runs={}  variables={}", len(m["runs"]), len(m["variables"])
            )
            t = time.time()
            for page in range(1, _MAX_PAGES + 1):
                r = (
                    await c.post(
                        "/graphql",
                        json={
                            "query": _LIGHTWEIGHT_QUERY,
                            "variables": {
                                "proposal": proposal,
                                "page": page,
                                "per_page": _PER_PAGE,
                            },
                        },
                    )
                ).raise_for_status()
                runs = r.json()["data"]["runs"]
                if not runs:
                    break
                if page == 1:
                    _dump_msg(runs, f"lightweight_table{page}")
                heavy = list(
                    {
                        v["name"]
                        for run in runs
                        for v in run["variables"]
                        if v["value"] is None
                    }
                )
                if heavy:
                    d = (
                        await c.post(
                            "/graphql",
                            json={
                                "query": _DEFERRED_QUERY,
                                "variables": {
                                    "proposal": proposal,
                                    "page": page,
                                    "per_page": _PER_PAGE,
                                    "names": heavy,
                                },
                            },
                        )
                    ).raise_for_status()
                    if page == 1:
                        _dump_msg(runs, f"deferred_table{page}")
            else:
                pkunit.pkfail("too many pages={}", page)
        pkdlog("graphql total: {:.3f}s  pages={}", time.time() - t, page + 1)

    with unit_util.server(_proposal_dir(kind)) as url:
        asyncio.run(_graphql(url))
