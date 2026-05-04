from damnit_api.pkcli import dev
import pykern.pkunit
import h5py
import pathlib
import sqlite3


def test_generate_proposal():
    def _assert_h5(path):
        with h5py.File(path, "r") as f:
            rd = f[".reduced"]
            assert set(f.keys()) == set(rd.keys()).union((".reduced", ".errors"))
            assert rd["simple_integer"][()] == 1
            assert b"128" in rd["numpy_2d_array"][()]

    def _assert_proposal(pdir, pnum, num_runs):
        assert pdir.joinpath("context.py").exists()
        assert len(list(pdir.joinpath("extracted_data").glob("*.h5"))) == num_runs
        _assert_h5(pdir.joinpath("extracted_data", f"p{pnum}_r1.h5"))
        _assert_db(pdir.joinpath(dev.DB_PATH), pnum, num_runs)

    def _assert_db(path, pnum, num_runs):
        c = sqlite3.connect(path)
        assert c.execute("SELECT count(*) FROM run_info").fetchone()[0] == num_runs
        assert c.execute(
            "SELECT count(*) FROM run_variables WHERE proposal=?", (pnum,)
        ).fetchone()[0] == num_runs * len(dev._VARIABLES)
        cols = [d[0] for d in c.execute("SELECT * FROM runs LIMIT 0").description]
        assert "run" in cols
        assert "simple_integer" in cols
        c.close()

    import time

    d = pathlib.Path(pykern.pkunit.empty_work_dir())
    dev.setup_test("small", d)
    s = dev._SETUP_TEST.small
    _assert_proposal(d.joinpath(str(s.proposal)), s.proposal, s.runs)
