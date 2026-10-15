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
