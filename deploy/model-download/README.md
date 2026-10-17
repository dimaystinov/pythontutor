# Browser model downloads

Public fixed endpoint: `https://dimaystinov.duckdns.org/model-download/qwen-yandex.zip`.

Nginx forwards this one path to `pythontutor-model-download.service` on `127.0.0.1:18766`. The service obtains a fresh URL for the public Yandex archive and streams its bytes without saving a ZIP on the server. It accepts GET, HEAD and OPTIONS, supports one byte range, permits CORS without credentials, and accepts no client-supplied upstream URL. Eight concurrent streams are allowed.

Installed paths: `/opt/pythontutor-model-download/proxy.py`, `/etc/systemd/system/pythontutor-model-download.service`; the Nginx location is included in the existing `dimaystinov.conf`. The pre-change config backup is `/etc/nginx/dimaystinov.before-model-cors-20261017.conf`. Validate with `nginx -t` before reloading. Stop/disable the service and remove only the exact model-download location to roll back without changing other routes.

The browser streams ZIP_STORED entries into verified WebLLM caches. It uses the ordinary server model directory and pinned HF/MLC URLs if this endpoint fails. No complete ZIP is retained on the device. Native Rust downloads continue using Yandex directly and a single app-data model directory.

Run `python3 -m unittest discover -s deploy/model-download -p 'test_*.py'` for the fixed-path streaming/CORS test. JS download and integrity tests are under `tutorial/static/tests/model-download.test.cjs`.
