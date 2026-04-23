# DAMNIT-web (RadiaSoft fork)

## Purpose

Improve the performance and modularization of [European-XFEL/DAMNIT-web](https://github.com/European-XFEL/DAMNIT-web).

We will use unit tests when possible to test performance and to help with refactoring.

The fork is maintained in this repo: [radiasoft/DAMNIT-web](https://github.com/radiasoft/DAMNIT-web).

RadiaSoft-specific work lives on `rs-*` branches.

## Current goal: API performance testing

Benchmark the FastAPI/GraphQL endpoints under realistic load. The existing `run/p6256/` dataset
is small (7 runs, each an HDF5 file with ~15 variables). Performance tests need a much larger
dataset — hundreds of runs with larger arrays — to surface bottlenecks.

### Plan

1. **Data generator** — a pkcli tool that synthesises a `run/` directory tree matching the real
   layout:
   - `run/<proposal>/extracted_data/<proposal>_r<N>.h5` — HDF5 files with the same variable
     groups as the real data (`.reduced`, `numpy_1d_array`, `numpy_2d_array`, `numpy_5d_array`,
     `plot_matplotlib`, scalar types, xarray, …)
   - `run/<proposal>/runs.sqlite` — populated SQLite database
   - `run/<proposal>/context.py` — context file

2. **pkcli module** — `api/src/damnit_api/pkcli/dev.py` (or similar) containing the generator
   commands, following the pykern pkcli convention. Needs a console entry point, e.g. `api/src/damnit_api/damnit_api_console.py` wired into
   `api/pyproject.toml` as a `[project.scripts]` entry so `damnit-api` is a runnable CLI.

3. **Performance tests** — pytest tests that start the API against the generated dataset and
   measure response times for key endpoints (metadata query, run list, variable data).

## Repo layout

```
api/                        FastAPI backend (Python 3.13, uv workspace)
  src/damnit_api/
    pkcli/                  pkcli commands (to be created)
    damnit_api_console.py   CLI entry point (to be created)
frontend/                   React/Vite frontend
run/                        Local data directory (gitignored)
  p6256/                    Real sample proposal
    extracted_data/*.h5     Per-run HDF5 files
    runs.sqlite
    context.py
scripts/                    Shell helpers
```

## Coding style

New RadiaSoft-authored files follow the local XFEL style (type annotations, Pydantic models,
FastAPI/Strawberry patterns) with these radiasoft-style improvements:

- **Qualified imports**: `import pykern.pkcli` then call as `pykern.pkcli.main(...)`, not
  `from pykern import pkcli`
- **Exceptions to qualified imports** (always import directly):
  - `from pykern.pkcollections import PKDict`
  - `from pykern.pkdebug import pkdc, pkdlog, pkdp`
- **Always keep the pkdebug import** even when none are currently used
- **Single-letter temporaries**: use `z`, `r`, `v` etc. for short-lived locals to signal
  limited scope and reduce line length; reserve longer names for parameters and module-level names
- **code org** sort alphabetically according to radiasoft-style skill
- **program functionally** remove unnecessary temporary variables
- **nested functions** one level nesting of functions (no deeper) are used to separate logical operations.


Other conventions:
- pykern is at `../radiasoft/pykern` (relative to this repo)
- HDF5 variable groups mirror the structure in `run/p6256/extracted_data/p6256_r1.h5` for now, but we'll create our own structure for the test data.

## Running the app locally

In a separate window, start the api server (VIRTUAL_ENV= suppresses a warning):

```bash
cd api
VIRTUAL_ENV= uv run -m damnit_api.main --path ../run/p6256
```

In another window, start the vite server:

```bash
cd frontend
pnpm run dev:app --port 8008
```

Make sure you tunnel 8008 and 8000 in order to visit http://localhost:8008.

## Dev installation (for RadiaSoft)

uv is a python environment manager. Installs cleanly as one binary in `~/.local/bin`:

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

7z is needed to unpack the compressed file given to RadiaSoft (cat prevents color output):

```bash
sudo dnf install -y p7zip  p7zip-plugins | cat
```

Create run directory, which assumes `~/tmp/p6256.7z`:

```bash
mkdir -p ~/src/radiasoft
cd ~/src/radiasoft
git clone https://github.com/radiasoft/DAMNIT-web
cd DAMNIT-web
mkdir -p run
cd run
7z x ~/tmp/p6256.7z
```

pnpm is a wrapper for npm. It has a complicated install to put one binary in place so clean that up after the curl installer:

```bash
curl -fsSL https://get.pnpm.io/install.sh | sh -
emacs ~/.bashrc # remove the lines added
mv ~/.local/share/pnpm/.tools/pnpm-exe/*.*.*/pnpm ~/.local/bin/
rm -rf ~/.local/share/pnpm
```

Install Vite and React:

```bash
cd frontend
echo VITE_API=http://localhost:8000 > apps/app/.env
# cat avoids color
pnpm install | cat
```
