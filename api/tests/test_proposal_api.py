from pykern.pkdebug import pkdc, pkdlog, pkdp


def test_basic():
    import asyncio
    import pathlib
    from pykern import pkunit
    from pykern.api import client
    from pykern.pkcollections import PKDict
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    async def _run(cfg, prop):
        async with client.Client(cfg) as c:
            a = PKDict(proposal=str(prop.proposal))
            r = await c.call_api(
                "table",
                PKDict(runs_per_page=100, start_page=1, **a),
            )
            pkunit.pkeq(prop.runs, len(r.runs))
            pkunit.pkeq(
                set(prop.variables.keys()).union(("proposal", "run")),
                set(x.name for x in r.runs[1].variables),
            )
            r = await c.call_api(
                "image",
                PKDict(run=1, variable="plot_matplotlib", **a),
            )
            pkunit.pkeq("rgba", r.dtype)
            pkunit.pkeq(bytes, type(r.data))

    d = pathlib.Path(pkunit.empty_work_dir())
    dev.setup_test("small", d)
    with unit_util.pykern_api_server(path=d) as c:
        asyncio.run(_run(c, dev._SETUP_TEST.small))
