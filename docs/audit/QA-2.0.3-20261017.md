# PythonTutor 2.0.3 — 2026-10-17

## Fresh verification
- Version updated consistently in npm, Cargo and Tauri metadata.
- JavaScript: 22 passed; Django: 52 passed; desktop bridge: 8 passed; Rust: 5 passed; CORS proxy: 1 passed.
- Native SQLite adapter and CLI registration checks passed.
- Real browser runtime: 11 checks passed, including tracing, timeouts/recovery, OpenCV and network isolation.
- Full real browser course: 134 tasks, 1302 tests, zero failures. Isolated QA page did not write learner progress.
- Native 2.0.3 UI: user logged in; built-in example moved from step 1/54 to 2/54 and completed with output and variable graph.
- OpenCode bundled CLI: correct explanation of -5 // 2; refused role-change request for a recipe. Both requests completed without TLS errors in this run.
- Native model store: all 92 files size/SHA-256 verified; no .part files.
- Browser sources: user server, Hugging Face and Yandex bridge each returned readable HTTP 206 ranges (1024 bytes). Raw Yandex fetch failed; bridge is required.
- Published browser downloader imported from GitHub Pages: first real ZIP entry fetched through bridge, SHA-256 checked, cached/read back; QA cache removed.
- macOS arm64 app and DMG built successfully. DMG integrity verified by hdiutil.
- DMG SHA256: 01ecf857117060abe25998b37ddac5861358cbc9ac131ceb3f446f6226a8a7fd.

## Findings and limits
- Native Qwen answered 17 % 5 correctly but failed the off-topic recipe request. Added deterministic checks for explicit role override and recognized unrelated topics before inference, and excluded those exchanges from model history. Fresh JS regression covers refusal before model loading, UI refusal with attachments, and valid educational examples. This is a targeted guard, not a guarantee against every off-topic formulation. Initial Qwen preparation/prefill was slow.
- Full 4.3 GB network download was not repeated; source checks used ranges and one real ZIP entry. Whole installed model was hashed separately.
- Windows build/runtime not executed on this Mac.

Final rebuild with the topic guard passed; hdiutil verified the replacement DMG. Native UI inference above was tested before the guard-only rebuild; the new guard was verified by JS and UI-handler regression tests, not a second native login session.
