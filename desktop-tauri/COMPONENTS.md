# Optional components (2.0.7)

The default tutor uses deterministic rules and curated hints in `guidance.js`. It
never loads a language model or sends a request to a provider. It uses the current
statement, allowed editor contents, and actual browser execution results. A stale
run cannot be used to diagnose edited code. It explains common Python exception
categories and compares test output; it does not claim to infer every logical bug.

LocalSpeech SDK 0.3.0 is an optional Russian ASR component (44,731,547 bytes). Its
runtime and small Zipformer model are served as versioned GitHub Pages assets.
They are excluded from both the course offline manifest and native installer.
All downloaded files are checked against the pinned SHA-256/size inventory in
`tutorial/static/pwa/local-speech-manifest.json`. Settings offers explicit install,
progress, cancellation and component deletion. Recognition is local and does not
upload audio. ASR itself uses a speech model; the default text tutor does not.

Reproduce optional Pages assets using the SDK checkout at commit 8db716c:

```
node tools/build-sdk.cjs --runtime-only
# SDK's separately downloaded, verified small/vad/context model files are required.
python scripts/prepare_speech_assets.py /path/to/local-speech
```

Run the second command in PythonTutor. Publish the generated
`dist/pages/static/local-speech/0.3.0/` directory alongside Pages. Keep SDK/model
notices and licenses. The source SDK is https://github.com/dimaystinov/local-speech.

Deletion is independent of learner reset: only component-owned caches or native
component directories are removed. Course pages, SQLite learner profiles, local
progress, editor drafts, and chat history remain. An active download must finish
or be cancelled first. Deleting the selected language model switches the tutor to built-in rules, preventing automatic redownload on reopening. Deleted components can be downloaded again. Native files
are shared between local profiles; removing a component affects all those profiles.

Validation on macOS: real Python missing-colon error; deterministic conversation
and test comparison tests; local speech recognition using synthetic Russian audio,
including after stopping the HTTP server; browser delete/reinstall and preserved
code, started-task state and chat; Rust tests for deletion boundaries and allowlisted
asset serving. Synthetic speech contained one extra word in recognition; this is
not an accuracy benchmark. Windows microphone behavior requires device testing.
