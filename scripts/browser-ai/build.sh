#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
npm ci --prefix scripts/browser-ai --no-audit --no-fund
scripts/browser-ai/node_modules/.bin/esbuild scripts/browser-ai/entry.mjs --bundle --format=esm --platform=browser --outfile=tutorial/static/vendor/webllm/webllm.mjs
python3 scripts/browser-ai/native-cache-patch.py
scripts/browser-ai/node_modules/.bin/esbuild scripts/browser-ai/voice-entry.mjs --bundle --format=esm --platform=browser --outfile=tutorial/static/vendor/transformers/transformers.mjs
cp scripts/browser-ai/node_modules/@huggingface/transformers/dist/ort-wasm-simd-threaded.jsep.mjs tutorial/static/vendor/transformers/
cp scripts/browser-ai/node_modules/@huggingface/transformers/dist/ort-wasm-simd-threaded.jsep.wasm tutorial/static/vendor/transformers/
