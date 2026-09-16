# Discovery Workbench Implementation Plan

Goal: ship a functioning bounded discovery instrument with objective evidence.
Architecture: dependency-free ESM mathematical core shared by a Web Worker and Node CLI; static browser UI; no backend. Spec: DESIGN.md.

- [x] Core: tests/engine.test.mjs first; run `node --test tests/engine.test.mjs` and retain red output. Implement engine.mjs with parseCSV(text), splitData(data, seed, mode), discover(data, options), predict(model, x), and makeDemo(kind). Repeat until regression tests pass.
- [x] Interface: tests/browser_test.py exercises built-in demo, local CSV, report export, invalid input, cancellation and 390px viewport. Implement index.html, styles.css, app.mjs, worker.mjs, and cli.mjs. Run Chromium and WebKit against the public HTTPS site, with requests and exceptions recorded. Sandbox navigation was blocked; no security policy was weakened.
- [x] Audit: independently reproduce selected coefficients in Python and verify final-target isolation. Produce benchmark JSON and documentation. Run all tests and a public-file allowlist/secret scan.
- [x] Ship: publish only this new repository under verified owner; configure public GitHub Pages using current CLI where connector lacks repository/Pages creation. Read back owner, commit, build status and deployed byte hashes. Exercise the live URL in a browser. Archive source/tests/evidence. No schedule, paid service, private source, or existing production change.

Review gates: scientific claims refer only to the measured fixture or partition. A failing challenge remains a result rather than a reason to hide data. Performance is not a novelty claim. Any hosted deployment failure is reported distinctly from packaged software delivery.

Execution receipt: `evidence/release.json`. The first hosted browser run failed on a CSP-incompatible test assertion; the harness was repaired without changing application security, and the next full run passed. Physical iPhone/Safari and visual screenshot review were not performed.
