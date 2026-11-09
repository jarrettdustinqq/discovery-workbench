# Browser CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the existing Chromium browser regression against every validated source revision.

**Architecture:** Extend `.github/workflows/ci.yml` with an independent
`browser` job. It creates an ephemeral Python virtual environment, installs the
pinned Playwright version and Chromium, then invokes the existing browser test
without `--url` so its built-in local server exercises the checkout. The manual
published-site workflow remains unchanged.

**Tech Stack:** GitHub Actions, Python venv, Playwright 1.62.0, Chromium,
existing Python browser test.

**Spec:** `docs/superpowers/specs/2026-11-08-browser-ci-design.md`

## Global Constraints

- Keep the existing engine job and manual receiver workflow unchanged.
- Use the current pinned action SHAs and Playwright version.
- Do not add scheduling, deployment, secrets, telemetry, or external services.

## Review Focus

- The browser test must target the checked-out revision, not the public Pages URL.
- Browser dependencies must remain runner-local and ephemeral.
- The job must run for both pull requests and `main` pushes inherited from the workflow trigger.
- A failure must block the workflow rather than be ignored.
- Existing engine validation must continue unchanged.

---

### Task 1: Add hosted Chromium browser coverage

**Files:**
- Modify: `.github/workflows/ci.yml`
- Test: GitHub Actions run for the pull request

**Interfaces:**
- Consumes: `tests/browser_test.py` with no `--url`, which starts a local static server.
- Produces: a required `browser` job that exits nonzero on an existing browser regression.

- [x] **Step 1: Add a `browser` job after `engine`**

Use Ubuntu 24.04, the existing pinned checkout/setup-node actions, an ephemeral
`$RUNNER_TEMP/browser-venv`, `playwright==1.62.0`, Chromium installation, and
`tests/browser_test.py --browser-engine chromium`.

- [x] **Step 2: Check workflow diff locally**

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 3: Push the branch and open a pull request**

Expected: the existing engine job and the new browser job are both scheduled.

- [ ] **Step 4: Verify hosted checks and main after merge**

Expected: both jobs pass on the PR and on the merged default-branch commit.
