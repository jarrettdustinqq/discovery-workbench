# Discovery Workbench

A local-first research instrument: find compact mathematical relationships, challenge them on withheld observations, and propose a measurement that could distinguish competing explanations.

**Release status:** 0.1.0 research preview, publicly deployed and tested. [Open the application](https://jarrettdustinqq.github.io/discovery-workbench/) · [Verified hosted test run](https://github.com/jarrettdustinqq/discovery-workbench/actions/runs/35038200654). The run passed 35 engine tests and 21 browser checks in each of Chromium and WebKit. See `evidence/release.json` for provenance and limits. This software is an AI-assisted implementation of bounded symbolic regression, not a general-purpose autonomous scientist, a frontier-model interface, or a claim of new scientific discovery.

## Run

Open the published HTTPS site, choose an example, and select **Discover & challenge**. No account, API key, model subscription, dataset upload, or backend is required. The site host receives normal page requests; user-supplied CSV is processed in a Web Worker in browser memory. An export deliberately includes the numeric dataset, so inspect it before sharing.

For a local static server, where your environment permits localhost browser navigation:

```sh
python3 -m http.server 8000
```

Then open the local server in a browser. Do not open `index.html` as a `file://` document: module-worker and secure-origin behavior differ across browsers. The CLI does not require a server:

```sh
node cli.mjs examples/polynomial.csv > result.json
node cli.mjs examples/norris.csv > reference-result.json
node --test tests/engine.test.mjs
```

Node 22 was used for verification. The application has no runtime npm or Python dependencies. Browser regression tests use a separately available Playwright installation and Chromium or WebKit; they are not required to use the app.

## Data contract

The first row contains unique identifier headers (letters, digits, underscores; start with a letter/underscore; at most 32 characters). Use 1–4 inputs and the target as the last column. Provide 30–2,000 rows with at least 30 distinct input groups. Files may be at most 1 MiB; values must be finite decimals of magnitude at most 1e6. Empty values, formulas, NaN, Infinity, inconsistent rows and malformed quoting are rejected, not silently imputed. Blank lines are ignored; explicitly empty CSV records are rejected.

Rows with exactly identical input vectors stay in the same partition. The seeded default allocates approximately 60/20/20 percent of **input groups**, not necessarily rows, to training, model selection and final testing. The optional ordered-group split is a stress test; it is not automatically a valid time-series or grouped-subject evaluation. Adjacent temporal observations, related subjects and approximate duplicates may still leak information. Structure such data appropriately before use.

## Method

A fixed grammar supplies individual inputs, squares, cubes, reciprocals, pairwise products and directed ratios. The expanded grammar adds sine, cosine, square-root-of-absolute-value and log-one-plus-absolute-value. The expression is an intercept plus at most three terms; coefficients are fitted by centered/scaled modified Gram–Schmidt QR on training data only. Singular candidates are rejected. Search keeps a beam of eight candidates per depth and permits at most 1,500 candidate fits. The browser terminates a run after 15 seconds; cancellation terminates the worker and discards partial results.

Candidate score:

```
validation_MSE / max(training_target_variance, 1e-12)
+ 0.0005 * expression_complexity
```

This is a heuristic, not a significance test or probability. The final-test target values influence neither candidate ranking nor experimental design. The winning coefficients are **not** refitted using held-out data. `supported_on_this_split` requires final-test R² above 0.5 and at least 20% less final MSE than a constant predictor based on the training mean. Thresholds are declared engineering defaults, not guarantees of usefulness or safety. A constant target has undefined R². An expression undefined on any final input is reported as an invalid result.

Near-best models within declared validation-score/error tolerances propose an unobserved-in-training point maximizing prediction range among 384 seeded samples plus corners of the **training-coordinate** box. A normalized nearest-neighbor distance above 0.15 triggers an off-support warning. No combinatorial feasibility, dimensional units, measurement costs, instrument limits or physical safety constraints are inferred. The proposal may be infeasible. Model disagreement is not calibrated uncertainty.

A new measured observation can be compared against the frozen model and appended. Appending invalidates the old result. Repeated inspection and tuning erode holdout independence; use genuinely new external measurements before trusting an adaptive result.

## Examples and provenance

- `polynomial.csv`: deterministic, noise-free synthetic data with planted relation `y = 1.7 + 2.4*a² + 0.8*b`. Recovery is an implementation check, not discovery of new physics.
- `confounded.csv`: deterministic synthetic observations with equal input sensors. Distinct models fit; proposed off-support measurements expose the ambiguity without resolving causality.
- `noise.csv`: deterministic independent pseudorandom inputs and targets. Failure to find support is a valid outcome.
- `norris.csv`: 36 published observed pairs from the NIST Norris ozone-monitor calibration reference dataset. NIST measurement is x and the customer measurement is y. Numeric pairs were transcribed from the retrieved official text and reordered into x,y CSV. No hash of the original downloaded file is claimed. Duplicate x values remain grouped.

Official NIST sources:
- Dataset and original numeric observations: https://www.itl.nist.gov/div898/strd/lls/data/LINKS/DATA/Norris.dat
- Study description: https://www.itl.nist.gov/div898/strd/lls/data/LINKS/i-Norris.shtml
- Certified **full-data** statistics: https://www.itl.nist.gov/div898/strd/lls/data/LINKS/v-Norris.shtml

The tool's default split fits only training rows and evaluates seven final rows for Norris. Those metrics are **not** NIST's certified full-data fit. `evidence/independent-check.json` records an independent NumPy calculation on the identical exported split, not independent data collection or an endorsement by NIST.

## Verify

```sh
node --test tests/engine.test.mjs
python3 tests/browser_test.py --browser-engine chromium --url https://jarrettdustinqq.github.io/discovery-workbench/
python3 tests/browser_test.py --browser-engine webkit --url https://jarrettdustinqq.github.io/discovery-workbench/
```

Core regressions include malformed input, grouped splits, determinism, polynomial/sinusoidal recovery, collinearity, constant targets, noise, undefined final-domain expressions, CLI parity, and final-target poisoning. Browser tests exercise demo runs, CSV selection, exports, new measurements, invalidation, cancellation, narrow viewport, cross-origin requests and uncaught exceptions. A test file alone is not proof it ran; consult the retained evidence.

## Security and scientific limits

No arbitrary expressions, eval, remote inference, plugin execution, physical actions, trading, telemetry or persistent dataset storage. UI text uses textContent; the Content Security Policy forbids connect requests, forms, objects and third-party scripts. Exports and screenshots can expose data the user deliberately supplied. The hosting provider may log ordinary page access. See GitHub Pages documentation: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages

No causal identification, dimensional analysis, automated literature search, proven novelty, exhaustive search, calibrated confidence intervals, independent real-world replication, scientific certification, medical decision support, industrial control or validated revenue generation is provided. Unsupported concepts outside the grammar cannot be found. Scale and numerical limits are explicit. Review any proposed real-world experiment separately.

## Ownership and deployment

New implementation prepared with AI assistance for GitHub owner `jarrettdustinqq`; no claim that the account owner manually authored the code. No additional software license grant is made here. Third-party reference data retain their provenance. Deployment does not prove external adoption, consequential scientific impact, or income.

Publication contains only this tool's new source, tests, synthetic examples and public NIST reference data. No existing repositories, credentials, private records, scheduled agents or production workloads are part of this release.
