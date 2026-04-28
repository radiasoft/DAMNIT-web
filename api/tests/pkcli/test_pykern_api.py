from pykern.pkdebug import pkdc, pkdlog, pkdp


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
