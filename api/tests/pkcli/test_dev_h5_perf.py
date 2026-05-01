import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DAMNIT_API_PERF_TEST"),
    reason="set DAMNIT_API_PERF_TEST to run",
)

_RUNS_PER_PAGE = 10


def test_h5_full_pipeline():
    """Full get_preview_data_from_path — server-side cost per cell (includes PNG encode)."""
    import time
    from pykern.pkdebug import pkdlog
    from damnit_api import data as _data
    from damnit_api.pkcli import dev

    def _run(p):
        t = time.time()
        for r in range(1, _RUNS_PER_PAGE + 1):
            for v in dev._PERF_VARIABLES:
                _data.get_preview_data_from_path(str(p), r, v)
        pkdlog(
            "h5 full pipeline: {:.3f}s  requests={}",
            time.time() - t,
            _RUNS_PER_PAGE * len(dev._PERF_VARIABLES),
        )

    _run(_proposal_dir())


def test_h5_raw():
    """Raw h5py read of full data datasets — pure I/O cost, no processing."""
    import h5py
    import time
    from pykern.pkdebug import pkdlog
    from damnit_api.pkcli import dev

    def _run(p):
        d = p.joinpath("extracted_data")
        t = time.time()
        for r in range(1, _RUNS_PER_PAGE + 1):
            with h5py.File(d.joinpath(f"p{dev.LARGE_PROPOSAL}_r{r}.h5")) as f:
                for v in dev._PERF_VARIABLES:
                    f[v]["data"][()]
        pkdlog(
            "h5 raw read: {:.3f}s  requests={}",
            time.time() - t,
            _RUNS_PER_PAGE * len(dev._PERF_VARIABLES),
        )

    _run(_proposal_dir())


def test_h5_reduced():
    """Raw h5py read of .reduced datasets — cost when pre-downsampled data is used."""
    import h5py
    import time
    from pykern.pkdebug import pkdlog
    from damnit_api.pkcli import dev

    def _run(p):
        d = p.joinpath("extracted_data")
        t = time.time()
        for r in range(1, _RUNS_PER_PAGE + 1):
            with h5py.File(d.joinpath(f"p{dev.LARGE_PROPOSAL}_r{r}.h5")) as f:
                for v in dev._PERF_VARIABLES:
                    f[".reduced"][v][()]
        pkdlog(
            "h5 reduced read: {:.3f}s  requests={}",
            time.time() - t,
            _RUNS_PER_PAGE * len(dev._PERF_VARIABLES),
        )

    _run(_proposal_dir())


def _proposal_dir():
    import pathlib
    from damnit_api.pkcli import dev
    from pykern import pkunit

    d = pathlib.Path(pkunit.empty_work_dir())
    p = d.joinpath(str(dev.LARGE_PROPOSAL))
    for c in (
        pathlib.Path(pkunit.data_dir()).joinpath("cache", str(dev.LARGE_PROPOSAL)),
        pathlib.Path(pkunit.data_dir()).parent.joinpath(
            "dev_perf_data", "cache", str(dev.LARGE_PROPOSAL)
        ),
    ):
        if c.exists():
            p.symlink_to(c)
            return p
    dev.setup_perf_test(str(d))
    return p
