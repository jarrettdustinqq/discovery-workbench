# Browser CI Design

## Intent

Catch browser-visible regressions in Discovery Workbench before source changes
merge, while preserving the existing manual published-site workflow as the
separate proof of GitHub Pages receiver behavior.

## Goals

- Run the existing Chromium browser regression suite on pull requests and
  pushes to `main`.
- Exercise the checked-out static site on a local HTTP server.
- Keep browser dependencies ephemeral to the GitHub-hosted runner.

## Non-goals

- Do not add a schedule, telemetry, a deployment, or a third-party service.
- Do not represent source CI as verification of the published Pages receiver.
- Do not alter the existing WebKit/manual published-site verification path.

## Approaches considered

1. Keep browser checks manual only. Lowest CI cost, but UI regressions remain
   undetected before merge.
2. Add a local Chromium job to the existing source workflow. It tests the
   checked-out revision before merge without depending on deployment timing.
3. Trigger the published-site workflow on every push. This can race the legacy
   Pages deployment and would blur source and receiver evidence.

Selected: approach 2. It improves merge-time behavioral coverage while leaving
receiver-side verification explicit and separately triggered.

## Acceptance

The GitHub workflow's new job installs its own Playwright environment, runs the
existing `tests/browser_test.py` without a URL so it serves the checkout
locally, and passes alongside the current engine job on a pull request.
