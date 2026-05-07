## How to Develop DAMNIT Web

DAMNIT uses [uv](https://docs.astral.sh/uv/) to configure and run
Python api and [pnpm](https://pnpm.io) to configure Typescript
frontend.

## One time: Dev installation (RadiaSoft style)

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

## Test data setup

To generate all test proposals:

```bash
cd api
rm -rf /tests/perf_data/cache
VIRTUAL_ENV= uv run damnit-api dev setup-db tests/perf_data/cache
ln -s api/tests/perf_data/cache ../run
```

## Start API

In a separate window, start the api server (VIRTUAL_ENV= suppresses a warning).
`--path` points to the proposals parent directory; all subdirs with `runs.sqlite` are discovered automatically.
This starts both the FastAPI server (port 8000) and the pykern.api WebSocket server (port 8001):

```bash
cd api
VIRTUAL_ENV= uv run -m damnit_api.main --path ../run
```

Clearing `VIRTUAL_ENV` avoids issues with Pyenv used at RadiaSoft vs uv.


Use `--pykern-port` to override the pykern.api port (default 8001):

```bash
VIRTUAL_ENV= uv run -m damnit_api.main --path ../run --pykern-port 8002
```

Use `DAMNIT_API_DATA_RGBA=1` to remove PNG conversion in damnit_api.data.get_preview_data:

```bash
DAMNIT_API_DATA_RGBA=1 VIRTUAL_ENV= uv run -m damnit_api.main --path ../run --pykern-port 8002
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

## Start Frontend

In another window, start the vite server:

```bash
cd frontend
pnpm run dev:app --port 8008
```

Make sure you tunnel 8008 and 8000. Port 8001 (pykern.api) is proxied
through Vite and does not need a separate tunnel.

- VITE_PYKERN_API=true - runs websocket + msgpack
- VITE_TABLE_ALL=true - turns off pagination

Visit http://localhost:8008
