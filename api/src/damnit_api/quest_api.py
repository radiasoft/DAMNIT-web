from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern.pkcollections import PKDict
import pykern.quest


class API(pykern.quest.API):

    async def api_extracted_data(self, api_args):
        from damnit_api.data import get_preview_data_from_path
        from damnit_api.shared.settings import settings
        return PKDict(get_preview_data_from_path(
            str(settings.damnit_path), api_args.run, api_args.variable
        ))

    async def api_ping(self, api_args):
        return PKDict(result="pong")
