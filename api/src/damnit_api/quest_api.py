from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern.pkcollections import PKDict
import pykern.pkconfig
import pykern.quest

cfg = pykern.pkconfig.init(
    damnit_path=(None, str, "Path to damnit proposal directory"),
)


class API(pykern.quest.API):

    async def api_extracted_data(self, api_args):
        import damnit_api.data
        return PKDict(
            damnit_api.data.get_preview_data_from_path(
                cfg.damnit_path, api_args.run, api_args.variable
            )
        )

    async def api_ping(self, api_args):
        return PKDict(result="pong")
