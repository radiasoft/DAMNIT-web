import asyncio
from collections.abc import AsyncGenerator

import strawberry
from async_lru import alru_cache
from strawberry.scalars import JSON

from ..db import async_latest_rows, async_table
from ..utils import create_map, wrap_values
from .metadata import fetch_metadata
from .models import DamnitRun, Timestamp
from .utils import DatabaseInput, LatestData, fetch_info

POLLING_INTERVAL = 1  # seconds


@alru_cache(ttl=POLLING_INTERVAL)
async def get_latest_data(proposal, timestamp):
    table = await async_table(proposal, name="run_variables")
    if table is None:
        return None

    latest_data = await async_latest_rows(
        proposal,
        table=table,
        by="timestamp",
        start_at=timestamp,
    )
    if not len(latest_data):
        return None

    latest_data = LatestData.from_list(latest_data)

    latest_runs = await fetch_info(proposal, runs=list(latest_data.runs.keys()))
    latest_runs = create_map(latest_runs, key="run")

    # New rows arrived. Clear the metadata cache so the next read is fresh.
    fetch_metadata.cache_invalidate(proposal)
    metadata = await fetch_metadata(proposal)

    runs = {}
    for run, variables in latest_data.runs.items():
        run_values = {
            name: {"value": data.value, "summary_type": data.summary_type}
            for name, data in variables.items()
        }
        run_values.setdefault("run", {"value": run})

        if run_info := latest_runs.get(run):
            run_values.update(wrap_values(run_info))

        runs[run] = DamnitRun.resolve(run_values)

    if not len(runs):
        return None

    assert latest_data.timestamp is not None  # noqa: S101 (we expect a timestamp!)

    # Use the union of the runs just in case `run_info` table is not synced
    # with the `run_variables` table.
    metadata = {
        "runs": sorted(set(metadata["runs"]) | set(runs.keys())),
        "variables": metadata["variables"],
        "timestamp": latest_data.timestamp * 1000,  # ms for JS
    }

    return {"runs": runs, "metadata": metadata}


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def latest_data(
        self,
        database: DatabaseInput,
        timestamp: Timestamp,
    ) -> AsyncGenerator[JSON]:  # FIX: # pyright: ignore[reportInvalidTypeForm]
        while True:
            # Sleep first :)
            await asyncio.sleep(POLLING_INTERVAL)

            result = await get_latest_data(
                proposal=database.proposal,
                timestamp=timestamp,
            )
            if result is not None:
                yield result  # FIX: # pyright: ignore[reportReturnType]
