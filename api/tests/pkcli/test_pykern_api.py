from pykern.pkdebug import pkdc, pkdlog, pkdp


def test_pykern_api_extracted_data():
    import asyncio
    import pathlib
    from pykern import pkunit
    from pykern.api import client
    from pykern.pkcollections import PKDict
    from damnit_api import unit_util
    from damnit_api.pkcli import dev

    async def _run(cfg):
        async with client.Client(cfg) as c:
            r = await c.call_api("extracted_data", PKDict(
                proposal=str(dev.SMALL_PROPOSAL),
                run=1,
                variable="simple_integer",
            ))
            pkunit.pkeq("number", r.dtype)
            pkunit.pkeq(1, r.data)

    d = pathlib.Path(pkunit.empty_work_dir())
    dev.setup_small_test(str(d))
    p = d.joinpath(str(dev.SMALL_PROPOSAL))
    with unit_util.pykern_server(path=p) as cfg:
        asyncio.run(_run(cfg))


def test_pykern_api_server():
    import asyncio
    from pykern import pkunit
    from pykern.api import client
    from pykern.pkcollections import PKDict
    from damnit_api import unit_util

    async def _run(cfg):
        async with client.Client(cfg) as c:
            r = await c.call_api("ping", PKDict())
            pkunit.pkeq(PKDict(result="pong"), r)

    with unit_util.pykern_server() as cfg:
        asyncio.run(_run(cfg))
