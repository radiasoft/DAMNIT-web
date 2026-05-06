from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import damnit.api
import damnit_api.data
import damnit_api.db
import damnit_api.graphql.models
import damnit_api.graphql.queries
import damnit_api.shared.const
import pykern.pkconfig
import pykern.quest


_cfg = pykern.pkconfig.init(
    damnit_path=(None, str, "Path to proposals parent directory"),
)


class API(pykern.quest.API):

    async def api_table(self, api_args):
        def _convert(row):
            for n, e in row.items():
                if e is not None:
                    yield _convert_var(n, e)

        def _convert_var(name, entry):
            t = damnit_api.graphql.models.DamnitRun.get_dtype(name, entry)
            v = entry.get("value") if isinstance(entry, dict) else entry
            if t != damnit_api.shared.const.DamnitType.IMAGE:
                v, t = damnit_api.graphql.models.serialize(v, dtype=t)
            return PKDict(name=name, value=v, dtype=t.value)

        async def _rows():
            return await damnit_api.graphql.queries.fetch_variables(
                api_args.proposal,
                limit=api_args.runs_per_page,
                offset=(api_args.start_page - 1) * api_args.runs_per_page,
            )

        return PKDict(
            runs=[PKDict(variables=tuple(_convert(x))) for x in await _rows()]
        )

    async def api_image(self, api_args):
        d = damnit.api.Damnit(
            damnit_api.db.find_proposal_path(_cfg.damnit_path, api_args.proposal)
        )[api_args.run, api_args.variable].read()
        return PKDict(
            data=damnit_api.data.get_rgba(d), shape=list(d.shape[:2]), dtype="rgba"
        )

    async def api_ping(self, api_args):
        return PKDict(result="pong")
