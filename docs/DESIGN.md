# Discovery Workbench 0.1 — implementation contract

Objective: turn the conversation's discovery / competing representations / falsification ideas into a usable, auditable research instrument. Do not claim superintelligence, new physics, causal identification, or automatic income.

Selected approach: a static, client-side symbolic model search tool. A cloud LLM laboratory would offer broader proposals but adds ongoing inference, account and execution dependencies. Extending unrelated income or governance projects would not directly test this conversation's idea. This tool uses the existing owner's GitHub infrastructure, without changing existing projects or schedules.

Scope: CSV ingestion (1–4 numeric inputs, final column target; 30–2,000 rows, 1 MiB), a bounded grammar of algebraic and optional elementary functions, training-only least-squares fitting, validation-ranked beam search, a held-out final evaluation, and a disagreement-driven next-measurement proposal. Competing models and limitations remain visible. CSV never executes as code. No arbitrary expressions, credentials, trackers, paid APIs, uploads, actuators, or trading.

Data contract: strict unique identifier headers; finite decimal numbers of magnitude <=1e6. Entire repeated-input groups stay in one partition. At least 30 distinct input groups. Seeded 60/20/20 group split; optional ordered-group stress test, not a time-series guarantee. Candidate fitting and preprocessing use training data only. Search uses validation targets; final targets cannot influence model selection or experiment design. Reruns after inspecting results require new external validation.

Model contract: intercept plus at most three terms. Standardized modified Gram–Schmidt QR fit. Reject singular and numerically invalid candidates. Complexity-penalized validation MSE ranks candidates. Constant baseline uses training mean. R² is undefined for constant targets. Nonfinite final predictions must be reported as failure, not silently omitted.

Experiment contract: propose an unobserved point inside observed coordinate ranges where comparably fitting models disagree. Flag off-support proposals and correlated inputs. Do not execute physical experiments; ranges are not physical feasibility checks. Disagreement is not calibrated predictive uncertainty.

Delivery: mobile-responsive static site, Node CLI, unit and browser tests, reproducible synthetic examples, source and evidence archive. GitHub publication under verified owner jarrettdustinqq, with no added license grant. Public release contains only new source, synthetic evidence, and explicitly sourced public NIST reference observations.

Acceptance: fixed synthetic polynomial recovered, noise rejected, constant/singular/malicious inputs handled; final-target poisoning cannot alter selected model; browser demo, CSV, export, cancellation and narrow viewport pass; live deployed bytes match tested source. Stop publication on failed core tests or secret scan, or if deployment requires new expenditure/privileged access. No claim of third-party adoption, scientific novelty, or profit from deployment alone.
