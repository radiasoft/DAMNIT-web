import pathlib
import sqlite3
import tempfile

import h5py
import numpy as np

from damnit_api.pkcli import dev


def test_generate_proposal():
    def _assert_h5(path):
        with h5py.File(path, "r") as f:
            rd = f[".reduced"]
            assert set(f.keys()) == set(rd.keys()).union((".reduced", ".errors"))
            assert rd["simple_integer"][()] == 1
            assert rd["numpy_2d_array"][()].tobytes()[1:4] == b"PNG"

    def _assert_proposal(proposal_dir, proposal, num_runs):
        assert proposal_dir.joinpath("context.py").exists()
        assert (
            len(list(proposal_dir.joinpath("extracted_data").glob("*.h5"))) == num_runs
        )
        _assert_h5(proposal_dir.joinpath("extracted_data", f"p{proposal}_r1.h5"))
        _assert_db(proposal_dir.joinpath(dev.DB_PATH), proposal, num_runs)

    def _assert_db(path, proposal, num_runs):
        c = sqlite3.connect(path)
        assert c.execute("SELECT count(*) FROM run_info").fetchone()[0] == num_runs
        assert c.execute(
            "SELECT count(*) FROM run_variables WHERE proposal=?", (proposal,)
        ).fetchone()[0] == num_runs * len(dev._VARIABLES)
        cols = [d[0] for d in c.execute("SELECT * FROM runs LIMIT 0").description]
        assert "run" in cols
        assert "simple_integer" in cols
        c.close()

    num_runs = 3
    with tempfile.TemporaryDirectory() as t:
        r = pathlib.Path(t)
        dev._generate_proposal(r, dev.SMALL_PROPOSAL, num_runs)
        _assert_proposal(
            r.joinpath(str(dev.SMALL_PROPOSAL)), dev.SMALL_PROPOSAL, num_runs
        )
