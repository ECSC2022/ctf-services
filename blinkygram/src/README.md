# Service sources


## Directory structure

- `out/`: build outputs (git-ignored).
- `src/`: sources.
    - `bot/`: bot service.
    - `common/`: common Python modules for protocol and client. Will be automatically copied to checkers, dist and exploits on `make dist`. Edit the source copy!
    - `docker/`: Dockerfiles and Docker Compose configurations.
    - `server/`: chat server.
- `test/`: testing tools (run with `src/common` in `PYTHONPATH`).
    - `bench_bot.py`: bot benchmarking tool.
    - `bench_server.py`: server benchmarking tool.
    - `test.py`: server and bot test suite.
- `tools/`: development tools (run with `src/common` in `PYTHONPATH`).
    - `chat.py`: simple chat client.


## Building

- `make`, `make dist`: build and copy to distribution directories.
- `make build`: build only.
- `make clean`: clean build outputs.
- `make distclean`: clean build outputs and distribution directories.
- `make format`: format code.


## Deterministic (Docker) builds

Run `./build.sh` to build within a Docker container.
The script is a wrapper over Dockerized `make`, and you can use it as if it was `make` (e.g., `./build.sh distclean`).
