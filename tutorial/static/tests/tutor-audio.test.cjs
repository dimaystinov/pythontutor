const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../js/tutor-audio-worklet.js'), 'utf8');
for (const sampleRate of [44100, 48000]) {
  let Processor; const blocks = [];
  const context = vm.createContext({sampleRate, Float32Array,
    AudioWorkletProcessor: class { constructor() { this.port = {postMessage: b => blocks.push(b)}; } },
    registerProcessor: (name, cls) => { assert.equal(name, 'tutor-pcm'); Processor = cls; }
  });
  vm.runInContext(source, context);
  const processor = new Processor();
  for (let pos = 0; pos < sampleRate * 2; pos += 128) {
    const input = new Float32Array(Math.min(128, sampleRate * 2 - pos)).fill(0.25);
    assert.equal(processor.process([[input]]), true);
  }
  const output = blocks.flatMap(b => Array.from(b));
  assert.ok(output.length >= 32000 - 2048 && output.length <= 32000);
  assert.ok(output.every(v => Math.abs(v - 0.25) < 0.0001));
  assert.equal(processor.process([]), true);
}
console.log('PASS microphone resampling 44.1/48 kHz → 16 kHz; bounded batches; silence without input');
