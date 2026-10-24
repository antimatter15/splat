const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const { test } = require('node:test');

// Exercise the actual worker without a browser or scene downloads.
const source = fs.readFileSync(process.env.SPLAT_SOURCE || path.join(__dirname, '..', 'main.js'), 'utf8');
const workerSource = source.slice(source.indexOf('function createWorker(self)'), source.indexOf('const vertexShaderSource'));

for (const [scale, expected] of [[2 ** -25, 0], [2 ** -13, 1], [0.5, 0x3c00]]) {
    test(`texture covariance at scale ${scale}`, () => {
        const messages = [];
        const self = { postMessage: message => messages.push(message) };
        const context = { self, console: { time() {}, timeEnd() {} }, setTimeout() {} };
        vm.runInNewContext(workerSource + '\ncreateWorker(self);', context);
        const buffer = new ArrayBuffer(32);
        new Float32Array(buffer).set([0, 0, 1, scale, scale, scale]);
        new Uint8Array(buffer).set([255, 128, 128, 128], 28);
        self.onmessage({ data: { buffer, vertexCount: 1 } });
        self.onmessage({ data: { view: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1] } });
        const texture = messages.find(message => message.texdata).texdata;
        assert.equal(texture[4] & 0xffff, expected);
        assert.equal(texture[5] >>> 16, expected);
        assert.equal(texture[6] >>> 16, expected);
    });
}
