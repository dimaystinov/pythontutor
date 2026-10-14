# Isolated Python runner

The web client (`evaldontevil.execute_python`) sends JSON to the internal
`POST /execute` endpoint with `Authorization: Bearer $RUNNER_TOKEN`. Both services
must share a random token of at least 32 characters. `RUNNER_URL` is required on
the web service. There is no host execution fallback.

Build the disposable image from the repository root:

```
docker build -f runner/Dockerfile.worker -t pythontutor-worker:local .
```

The control plane runs `python -m runner.server`, on port 8081. Its `RUNNER_IMAGE`
defaults to `pythontutor-worker:local`. Only the control plane receives the Docker
socket. Never publish its port on a public interface. `/healthz` is a liveness
check, not a Docker readiness check. A Docker failure returns `internal_error`.

Each job starts a fresh Python 3.14.7 container: UID/GID 65534, no network, no host
mounts, read-only root filesystem, all capabilities dropped, no privilege gains,
512 MiB RAM without extra swap, 32 processes, one CPU, 10 CPU seconds and 10 wall
seconds (including startup). Temporary files have an 64 MiB tmpfs. The runner
always attempts forced container removal, including after timeout. Docker's
default seccomp profile remains enabled. Containers are an isolation layer, not
a guarantee against kernel vulnerabilities; keep Docker and the host patched.

Source and input each have a 64 KiB UTF-8 limit. Captured output has a 64 Ki
character limit per stream, trace has at most 1,000 steps and 2 MiB of serialized
snapshots, and the control plane rejects combined raw output over 8 MiB even
when code bypasses Python stream capture. Four simultaneous jobs are allowed;
excess requests fail closed. Traces retain the archived visualizer's tags and
field names, with bounded collections/depth and descriptor-free object display.
Only uncaught exceptions make a job fail; caught exceptions remain trace events.

Run protocol tests:

```
.venv/bin/python -m pytest runner/tests evaldontevil/executor_test.py -q
RUN_DOCKER_TESTS=1 .venv/bin/python -m pytest runner/tests -q
```

The second command requires the built image and live Docker daemon. It exercises
network isolation, denied root filesystem writes, absent Docker socket/token,
CPU/wall timeouts and raw-output limits. Individual grading tests intentionally
run in separate containers; large task test suites incur container startup cost.

## Images and OpenCV

The worker includes pinned OpenCV headless 5.0.0.93, NumPy 2.5.3 and Pillow
12.3.0 wheels (`requirements.lock`). BLAS/OpenMP thread counts default to one.
An optional `image` field contains bare base64 PNG/JPEG bytes, at most 2 MiB and
4 million pixels. Input is decoded and stripped of metadata into `input.png` in
an ephemeral working directory. Image input disables tracing. Save processing
results to `output.png`; regular files only, no symlinks or special files.
The result's optional `image` is bare base64 PNG. Both worker and control plane
independently decode and normalize output, stripping metadata. Invalid images
return `invalid_image`. File bytes and normalized PNG must both fit 2 MiB.
RGBA is normalized to RGB. No other files are exported. Control plane image
validation is included within its four-job concurrency limit.

After building both runner and worker images, verify the complete control-plane
image (including its Docker CLI) with:

```
RUN_CONTROL_PLANE_TESTS=1 .venv/bin/python -m pytest runner/tests/test_controlplane.py -q
```

This starts an ephemeral hardened runner container with the Docker socket,
sends an authenticated HTTP request, and checks the child worker's Python
version and output. The runner image installs Debian's `docker-cli` package;
no Docker daemon is installed inside that image.
