# DAMNIT-web (RadiaSoft fork)

## Purpose

Improve the performance and modularization of [European-XFEL/DAMNIT-web](https://github.com/European-XFEL/DAMNIT-web).

We will use unit tests when possible to test performance and to help with refactoring.

The fork is maintained in this repo: [radiasoft/DAMNIT-web](https://github.com/radiasoft/DAMNIT-web).

RadiaSoft-specific work lives on `rs-*` branches.

## Customer requests
Each field in DAMNIT can have underlying data stored in an HDF5 (H5) file, which may contain multi-dimensional arrays such as an image or a time-series.
We have an existing solution for making these datasets accessible and explorable, and we need your help improving it.

Specifically, we need your help with three things:

1. Visualisation performance - Currently the full array is serialised and sent to the frontend in one request. For large amounts of data this can be slow to load and cause performance issues in the browser with Plotly. We'd like advice on: implementing backend-side downsampling/slicing so only the visible portion is transferred, a loading pattern that supports progressive/incremental data fetching as the user interacts with the plot, and to learn more about the importance/impact of using an improved transport mechanism (e.g. MessagePack, typed arrays) to replace JSON.
2. Visualisation interactivity/features - The structure of the underlying data is variable, so the xarray-like data sent to the frontend (data, dims, coords, attrs) is also variable. This makes it difficult to implement advanced plotting features in the frontend, since it doesn't have an easy way to get information about what kind of plot it should be creating. We'd like advice on: how to build and support interactive visualisations (pan, zoom, slice selection, value inspection) on the frontend given this dynamic data (while supporting the downsampling from point 1).
3. Table formatting/interactivity - Similarly to (2): the dynamic nature of the context file means that the tables do not have a schema, the columns and their types are not stable or well defined. The columns potentially containing anything makes implementing 'standard' table features like column-level formatting (colours, units, conditional formatting), search, sort, filtering, etc..., quite awkward. We'd like advice on how to handle supporting these features given our use case of dynamic column types.

## Rob's notes from meeting 4/17/26

This is in emacs org mode.

```txt
* meeting: Luca, Cammille, Robert, Paul, Rob
** Visualisation performance
*** XFEL: Currently the full array is serialised and sent to the frontend in one
request. For large amounts of data this can be slow to load and cause
performance issues in the browser with Plotly. We'd like advice on:
implementing backend-side downsampling/slicing so only the visible
portion is transferred, a loading pattern that supports
progressive/incremental data fetching as the user interacts with the
plot, and to learn more about the importance/impact of using an
improved transport mechanism (e.g. MessagePack, typed arrays) to
replace JSON.
*** RS: msgpack, websockets will improve performance
    push more code to the python and use a simpler renderer as
    the front end.
    timeseries viewer in sirepo use a frame at a time (can fetch
       ahead/behind with local cache)
    perhaps plotly is the wrong tool
** Visualisation interactivity/features
*** XFEL: The structure of the underlying data is variable, so the xarray-like
data sent to the frontend (data, dims, coords, attrs) is also
variable. This makes it difficult to implement advanced plotting
features in the frontend, since it doesn't have an easy way to get
information about what kind of plot it should be creating. We'd like
advice on: how to build and support interactive visualisations (pan,
zoom, slice selection, value inspection) on the frontend given this
dynamic data (while supporting the downsampling from point 1).
*** RS: compile (JIT) sqlite/context into a schema that drives
    the UI and backend for each proposal. again, push more code to
    python and have the UI driven by the python and schema
  Step away from code that's (attempted to be) statically typed to a
      dynamic types in python and javascript so can interpret
      structures based on metadata sent with the structure.
  build out widget hiearchy from schema. when context/sqlite variables
     change, then refresh the window. each variable might be null if
     it was added after the run was processed
  we use d3js, and we handle for example value inspection RS code
     pan/zoom is done by d3js. mapping to a canvas done by RS code.
     slice is handled by RS code. we navigate through frames over a
     dim (e.g time or z)
** Table formatting/interactivity
*** XFEL: Similarly to (2): the dynamic nature of the context file means that
the tables do not have a schema, the columns and their types are not
stable or well defined. The columns potentially containing anything
makes implementing 'standard' table features like column-level
formatting (colours, units, conditional formatting), search, sort,
filtering, etc..., quite awkward. We'd like advice on how to handle
supporting these features given our use case of dynamic column types.
*** RS: handle search, for example, by dynamically parsing the query in
    the backend to map to run variables, etc. treating missing columns
    is tricky, but possible with semantics. we handle this dynamic
    code in slactwin (perhaps demo).
    all the metadata (color, etc.) is handled on the server and the ui
       is rendering based on that interpretation on the server
       (which is closer to the data)
    sorting is handled server side. sometimes you can't sort. again,
       server decides.
** RS: damnit_api.data
78 reqeusts 10MB on startup
b64 encoding of the images then json => msgpack
graphql used minimally maybe not the right approach
    typescript table code is too specific and seems overly complicated
    glidapps is fast but a bit awkward, e.g. no copy paste so unnatural
        although flexible
    the data in this table is less complex because it is heavily
        downsampled so a different solution might be more flexible
** for the rest of the project
*** analyze performance in detail/create test env
demo doesn't have enough data
if we get working data (large hdf5, sqlite) from a few projects, damnit-api
code, and run damnit api
ideally we would have this on our computers
different schemas
would workaround oauth
outcome would be suggestions for improvement to damnit-web & api
*** tutorial is problematic
need to categorize problems based on data
then write tutorial, but not enough money for this
could just teach generically but not much value
* notes
Robert thinks the only right way to handle run variable types is to formerly create
  structure. he doesn't like the current strucutre, because you don't
  know the type. I told him you can infer the type and denormalize
  that.
Cammille thinks there needs to be flexibility, but doesn't know how to
  handle.
The types of the value can change over time from a string, int, integer.
users would like to be able to use spreadsheets to manipulate the
  data. I suggested they allow it.
Luca liked the idea of us digging in. Cammille is preparing a test
  environment.
we will then proceed by working on performance problem first. there
  won't be a workshop. Luca will confirm with Steffen.
Robert would like more type information in the context file and sqlite
  db. Types are very limited or unknown. Some columns could have
  multiple different data types, such as float and array?
They have 1000s of users. An average project is 100s of runs, with
  the max number of runs around 5000.
They would like to filter/sort, and think graphql could simplify
  this.
Luca said the PyQt version is feature rich and they would eventually
  like the web app to achieve parity.
They have "expert" users who prefer to work with the data in Google
  Sheets or Excel.
They don't expose the web API publicly.
```

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

## Test data setup

`run` is a symlink to `api/tests/perf_data/cache`. To regenerate all test proposals after changing data generation code:

```bash
cd api
rm -rf /tests/perf_data/cache
VIRTUAL_ENV= uv run damnit-api dev setup-db tests/perf_data/cache
```

## Running the app locally

In a separate window, start the api server (VIRTUAL_ENV= suppresses a warning).
`--path` points to the proposals parent directory; all subdirs with `runs.sqlite` are discovered automatically.
This starts both the FastAPI server (port 8000) and the pykern.api WebSocket server (port 8001):

```bash
cd api
VIRTUAL_ENV= uv run -m damnit_api.main --path ../run
```

Use `--pykern-port` to override the pykern.api port (default 8001):

```bash
VIRTUAL_ENV= uv run -m damnit_api.main --path ../run --pykern-port 8002
```

To run the pykern.api server standalone (e.g. for interactive testing without FastAPI):

```bash
cd api
DAMNIT_API_QUEST_API_DAMNIT_PATH=../run VIRTUAL_ENV= uv run python -c "
from pykern.api import server
from pykern.pkcollections import PKDict
from damnit_api import quest_api
server.start(api_classes=[quest_api.API], attr_classes=[], http_config=PKDict(api_uri='/api-v1', tcp_ip='127.0.0.1', tcp_port=8001))
"
```

In another window, start the vite server:

```bash
cd frontend
pnpm run dev:app --port 8008
```

Make sure you tunnel 8008 and 8000. Port 8001 (pykern.api) is proxied
through Vite and does not need a separate tunnel.

- VITE_PYKERN_API=true - runs websocket + msgpack
- VITE_TABLE_ALL=true - turns off pagination

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
