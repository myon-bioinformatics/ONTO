import json
import shutil
import subprocess
import unittest

from knowledgegraph import mermaid_renderer_js


class RendererTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node required for module execution")
    def test_lazy_shared_renderer(self):
        # Substitute an in-memory module so verification works without the CDN.
        source = mermaid_renderer_js()
        url = "https://cdn.jsdelivr.net/npm/mermaid@11.12.1/dist/mermaid.esm.min.mjs"
        self.assertEqual(source.count(url), 1)
        script = """
import assert from 'node:assert/strict';
const moduleURL = text => 'data:text/javascript;base64,' + Buffer.from(text).toString('base64');
globalThis.events = [];
const stub = moduleURL(`events.push('loaded'); export default {
  initialize(options) { events.push(options); },
  render(id, source) { return {svg: id + ':' + source}; }
};`);
const {renderDiagram} = await import(moduleURL(SOURCE.replace(URL_LITERAL, stub)));
assert.deepEqual(events, []);
assert.deepEqual(await Promise.all([renderDiagram('a','A'), renderDiagram('b','B')]), ['a:A','b:B']);
assert.deepEqual(events, ['loaded', {startOnLoad:false, securityLevel:'strict'}]);
"""
        script = script.replace("SOURCE", json.dumps(source)).replace("URL_LITERAL", json.dumps(url))
        subprocess.run(["node", "--input-type=module", "-"], input=script, text=True, check=True)
