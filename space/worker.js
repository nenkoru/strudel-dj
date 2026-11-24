// Runs the model off the page's thread. Messages in: {type: 'load', variant} and {type: 'generate', prompt,
// options}. Out: progress, ready, token, done, error. Generation is synchronous: to stop it, the page ends
// this worker and starts a new one (the weights then come from Cache Storage).
import { StrudelLM } from './model.mjs';

const BASE = 'https://huggingface.co/nenkoru/strudel-dj-129m/resolve/main/';
const CACHE = 'strudel-dj-129m-int8-v1';
let model = null;

onmessage = async ({ data }) => {
  try {
    if (data.type === 'load') {
      let last = 0;
      const t0 = performance.now();
      model = await StrudelLM.load(`${BASE}${data.variant}/`, {
        cache: CACHE,
        onProgress: ({ loaded, total }) => {
          if (loaded - last < 1 << 20 && loaded !== total) return;
          last = loaded;
          postMessage({ type: 'progress', loaded, total });
        },
      });
      postMessage({ type: 'ready', backend: model.backend, ms: performance.now() - t0 });
    } else if (data.type === 'generate') {
      const t0 = performance.now();
      const result = model.generate(data.prompt, {
        ...data.options,
        onToken: (count, text) => { if (count % 4 === 0) postMessage({ type: 'token', count, text }); },
      });
      postMessage({ type: 'done', ...result, ms: performance.now() - t0 });
    }
  } catch (e) {
    postMessage({ type: 'error', message: String(e?.message || e) });
  }
};
