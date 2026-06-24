# Browser Download Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default direct API downloader with browser automation that reproduces the confirmed DataWeb manual download flow.

**Architecture:** Keep task definitions and file naming in `tasks.py`, keep config parsing in `config.py`, and add a focused `browser_downloader.py` for Playwright page actions and download capture. The CLI orchestrates tasks, manifest logging, skip-existing behavior, and row-count warnings.

**Tech Stack:** Python 3, PyYAML, Playwright for Python, unittest.

---

### Task 1: Lock New Task Semantics

**Files:**
- Modify: `tests/test_tasks.py`
- Modify: `usitc_dataweb/tasks.py`

- [ ] Add tests proving default one-month task count is 23 and filenames no longer include HTS suffixes.
- [ ] Run `python -m unittest tests.test_tasks` and verify the new tests fail before changing implementation.
- [ ] Update `build_tasks` and `make_filename` so split prefixes are not used by default.
- [ ] Run `python -m unittest tests.test_tasks` and verify it passes.

### Task 2: Update Runtime Config

**Files:**
- Modify: `tests/test_config.py`
- Modify: `usitc_dataweb/config.py`
- Modify: `configs/default.yaml`
- Modify: `configs/sample_small.yaml`

- [ ] Add tests for browser runtime fields: `download_timeout_seconds`, `headless`, and no default HTS2 split.
- [ ] Run `python -m unittest tests.test_config` and verify failures.
- [ ] Update config parsing and YAML files to remove default HTS2 chapter lists and add browser runtime settings.
- [ ] Run `python -m unittest tests.test_config` and verify it passes.

### Task 3: Add Browser Downloader

**Files:**
- Create: `usitc_dataweb/browser_downloader.py`
- Modify: `requirements.txt`

- [ ] Add Playwright dependency.
- [ ] Implement a `BrowserDownloader` class with methods to open DataWeb, apply task settings, click download, wait for the download, and save using the task output path.
- [ ] Use robust labels/roles first and DOM fallbacks for DataWeb controls whose accessible names are unstable.
- [ ] Do not use proxy settings for DataWeb.

### Task 4: Wire CLI to Browser Mode

**Files:**
- Modify: `usitc_dataweb/__main__.py`
- Modify: `README.md`

- [ ] Replace default direct `dataExport` calls with `BrowserDownloader`.
- [ ] Keep `--dry-run` for task listing/payload diagnostics without browser download.
- [ ] Keep `--limit` for smoke tests.
- [ ] Remove `--no-split` from documented default workflow.
- [ ] Update README with install command including `playwright install chromium`, default 23-task behavior, and download naming.

### Task 5: Verify

**Files:**
- No planned source changes.

- [ ] Run `python -m unittest discover -s tests`.
- [ ] Run `python -m compileall -f usitc_dataweb tests`.
- [ ] Run `python -m usitc_dataweb --config configs/sample_small.yaml --dry-run --limit 1`.
- [ ] If Playwright browsers are installed, run one real `--limit 1` smoke test and report whether DataWeb download completed.

