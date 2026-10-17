# PythonTutor — Rust + Tauri 2

Native Windows/macOS application. The installer includes all 316 course pages, 134 Python problems with 1,302 tests, the vendored Pyodide runtime, OpenCV learning images, and the official OpenCode CLI (pinned 1.19.0; GitHub release SHA-256 verified at build time). No user-installed Python, Node, server, API key, pairing code or model download is needed for cloud assistance. MiMo Free needs internet and is subject to provider availability; no paid fallback.

Local registration/login uses Argon2 salted password hashes. Solutions live in SQLite under Tauri app_data_dir (`org.pythontutor.desktop`); drafts and chat history use profile-prefixed WebView storage. No central account server or password recovery service. Each application launch starts at login. Autostart is optional at login; it starts hidden with a tray menu. The course stays offline, and the native assistant calls the bundled CLI through restricted Rust commands.

OpenCode runs with isolated temporary config/data/cache directories, no plugins, no inherited OPENCODE configuration, `permission: ask` and no auto-approval. Its noninteractive command rejects tools. Cancellation/timeout terminates the subprocess. No general shell commands are exposed to JavaScript. External web pages cannot navigate inside the privileged WebView.

Build:

1. Install Rust, Node and platform Tauri build prerequisites.
2. Install Django 5.2, whitenoise, requests, Pillow in build Python.
3. `python desktop-tauri/prepare.py`
4. `cd desktop-tauri && npm ci`
5. `cargo test --manifest-path src-tauri/Cargo.toml`
6. `npm run build`

`prepare.py` builds a separate native frontend; it does not modify the GitHub Pages frontend. Packaged binaries and generated course files are not committed. GitHub Actions builds Windows NSIS, Mac ARM64 DMG and Mac Intel DMG. Signing certificates are not yet configured; this is a prerelease until platform UI checks are complete.

### OpenCode в терминале

Windows NSIS добавляет `%LOCALAPPDATA%\PythonTutor\bin` в пользовательский PATH
при установке и удаляет только эту запись при удалении приложения.
На macOS DMG не выполняет установочные скрипты: при первом запуске PythonTutor
копирует CLI в `~/.local/share/pythontutor/bin` и добавляет этот каталог в настройки
zsh/bash. Откройте новый терминал и выполните `opencode --version`.
Существующая установка OpenCode, расположенная раньше в PATH, имеет приоритет.
Проверка регистрации без изменения личных настроек: `python3 install/test_cli.py`.

## Local Qwen storage

Choosing Qwen starts a Rust-managed installation automatically. The installer checks the pinned manifest, tries the single Yandex ZIP, then the server and pinned Hugging Face files. The WASM runtime fallback is the official pinned MLC repository. Downloads are written to temporary files and checked for size and SHA-256 before installation.

The sole persistent copy is `app_data_dir/models/qwen7b`. Native WebLLM uses the `native-file` backend, which reads the Tauri asset protocol with `cache: no-store`; it does not copy weights into CacheStorage, IndexedDB or OPFS. The installer removes its ZIP and temporary files after success. An old Qwen browser cache in the app origin is cleaned only after disk verification. User Downloads and unrelated caches are not deleted by the installer. Browser builds retain their normal cache behavior.

The vendored backend extension is reapplied by `scripts/browser-ai/native-cache-patch.py` when rebuilding WebLLM. Native inference still requires WebGPU with shader-f16. A missing GPU does not silently route questions to cloud services.
