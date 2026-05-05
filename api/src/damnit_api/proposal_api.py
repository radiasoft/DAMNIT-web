from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import damnit.api
import damnit_api.data
import damnit_api.db
import pykern.pkconfig
import pykern.quest


_cfg = pykern.pkconfig.init(
    damnit_path=(None, str, "Path to proposals parent directory"),
)


class API(pykern.quest.API):

    async def api_table(self, api_args):
        from damnit_api.graphql.queries import fetch_variables

        return PKDict(
            runs=await fetch_variables(
                api_args.proposal,
                limit=api_args.runs_per_page,
                offset=(api_args.start_page - 1) * api_args.runs_per_page,
            )
        )

    async def api_image(self, api_args):
        import damnit_api.db

        p = damnit_api.db.find_proposal_path(_cfg.damnit_path, api_args.proposal)
        d = damnit.api.Damnit(p)[api_args.run, api_args.variable].read()
        return PKDict(
            data=damnit_api.data.get_rgba(d), shape=list(d.shape[:2]), dtype="rgba"
        )

    async def api_ping(self, api_args):
        return PKDict(result="pong")
