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
            r = await c.call_api(
                "extracted_data",
                PKDict(
                    proposal=str(dev._SETUP_TEST.small.proposal),
                    run=1,
                    variable="simple_integer",
                ),
            )
            pkunit.pkeq("number", r.dtype)
            pkunit.pkeq(1, r.data)

    d = pathlib.Path(pkunit.empty_work_dir())
    p = dev.setup_test("small", str(d))
    with unit_util.pykern_api_server(path=p) as cfg:
        asyncio.run(_run(cfg))


def test_pykern_pykern_api_server():
    import asyncio
    from pykern import pkunit
    from pykern.api import client
    from pykern.pkcollections import PKDict
    from damnit_api import unit_util

    async def _run(cfg):
        async with client.Client(cfg) as c:
            r = await c.call_api("ping", PKDict())
            pkunit.pkeq(PKDict(result="pong"), r)

    with unit_util.pykern_api_server() as cfg:
        asyncio.run(_run(cfg))
