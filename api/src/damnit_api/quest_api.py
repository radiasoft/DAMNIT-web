from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern.pkcollections import PKDict
import pykern.quest


class API(pykern.quest.API):

    async def api_ping(self, api_args):
        return PKDict(result="pong")
