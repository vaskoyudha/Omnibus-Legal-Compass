# Omnibus Legal Compass — Full Open Source Transformation

## TL;DR

> **Quick Summary**: Transform the existing Indonesian Legal RAG system ("Omnibus Legal Compass") from a working project into a professional, standout open-source repository with competitive features, full test coverage, documentation site, and showcase-quality presentation — establishing it as the world's first and only Indonesian legal AI tool.
>
> **Deliverables**:
> - Security-hardened repository (purged secrets, .env protection)
> - Professional OSS infrastructure (LICENSE, CONTRIBUTING, CI/CD, templates)
> - Full Knowledge Graph with temporal versioning and cross-references
> - Multi-turn chat with conversation history
> - API-first design with OpenAPI spec
> - Visual Compliance Dashboard (law coverage heat map)
> - VitePress documentation site
> - Showcase README with screenshots/demos/GIFs
> - Competitive comparison table
> - Comprehensive TDD test suite (>80% backend coverage)
> - All existing LSP/type errors fixed
>
> **Estimated Effort**: XL (22 tasks across 8 parallel waves)
> **Parallel Execution**: YES — 8 waves
> **Critical Path**: Task 1 (security) → Tasks 2-4 (infra) → Tasks 5-8 (tests+fixes) → Tasks 9-12 (features) → Tasks 13-17 (features) → Tasks 18-19 (docs+README) → Task 20 (comparison) → Tasks 21-22 (demo+launch)

---

## Context

### Original Request
User wants to transform "Regulatory Harmonization Engine" (an Indonesian Legal RAG system) into a professional open-source project that:
1. Looks and feels like a top-tier OSS repository (Supabase/Cal.com quality)
2. Has clear competitive advantages over similar projects globally
3. Attracts developers, legal professionals, businesses, and the RegTech community
4. Demonstrates the project's unique value as the FIRST Indonesian legal AI

### Interview Summary
**Key Discussions**:
- **Branding**: Official name is "Omnibus Legal Compass" (rename from "Regulatory Harmonization Engine")
- **Scope**: Stay Indonesia-focused (deep specialization strategy)
- **Plan scope**: Full transformation — OSS packaging + 7 new features
- **Community**: Minimal — just excellent documentation, no Discord/Discussions needed
- **License**: MIT — maximum freedom, most trusted
- **Testing**: Comprehensive TDD with >80% backend coverage
- **README**: Full Supabase-style showcase — BUT existing UI design/flow MUST NOT be broken
- **Knowledge Graph**: Full (temporal versioning, cross-references, hierarchical UU→PP→Perpres)
- **Playground**: Screenshots/demos/GIFs only (no live deployment, zero API cost)
- **Docs site**: VitePress, English only, GitHub Pages
- **Dashboard**: Law coverage heat map (indexed vs missing articles)

**Research Findings**:
- **Zero direct Indonesian competition** — first-mover advantage in blue ocean
- **73% of legal AI competitors have NO frontend** — Next.js app is a major differentiator
- **Only 13% have hybrid search, 7% have reranking** — existing tech is already top-tier
- **CRITICAL security issue**: `.env` with live NVIDIA API key committed to git history
- **Missing OSS infrastructure**: No LICENSE file, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY.md, CI/CD, issue/PR templates
- **LSP type errors** in `backend/main.py` and `backend/retriever.py`
- **Top competitors**: Lawyer LLaMA (980★, Chinese only), Fuzi.mingcha (365★, Chinese only), AI Legal Compliance (311★, NY alcohol only)

### Metis Review
**Identified Gaps** (addressed):
- **Knowledge Graph scope explosion risk**: User confirmed FULL graph is desired (temporal + cross-refs + hierarchy) — tasks are structured incrementally
- **API-first definition ambiguity**: Resolved as auto-generated OpenAPI from FastAPI, public read-only, no auth in V1
- **Playground vagueness**: Resolved as screenshots/demos/GIFs only — zero API cost
- **Dashboard metrics**: Resolved as law coverage heat map (indexed vs missing)
- **Testing non-deterministic LLM outputs**: Plan uses fuzzy matching for RAG tests + retrieval-only tests separated from generation
- **Legal disclaimer requirement**: Added to UI footer + README + docs
- **Rate limiting for API**: Added FastAPI slowapi for public endpoints
- **Citation hallucination risk**: Post-processing validation against indexed documents added to KG task

---

## Work Objectives

### Core Objective
Transform Omnibus Legal Compass into a world-class open-source Indonesian legal AI project with competitive features, professional infrastructure, and showcase-quality presentation.

### Concrete Deliverables
1. Security-purged git repository with `.env` removed from all history
2. `LICENSE` (MIT), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` files
3. `.github/` with issue templates, PR template, CI/CD workflows
4. All LSP type errors in backend fixed (zero errors)
5. Comprehensive test suite: >80% backend coverage, frontend component tests
6. Knowledge Graph: full ontology (Law → Chapter → Article + cross-refs + temporal versioning + hierarchy)
7. Multi-turn chat: 10-message sliding window, in-memory
8. API-first: OpenAPI spec auto-generated from FastAPI with enhanced descriptions
9. Visual Compliance Dashboard: law coverage heat map (Recharts)
10. VitePress documentation site (5+ core pages) deployed to GitHub Pages
11. Showcase README: banner, badges, GIF demos, architecture diagram, quick-start, comparison table
12. Competitive comparison table (vs 5 global legal AI projects)
13. Demo screenshots/GIFs for README and docs
14. Rate limiting on all public API endpoints
15. Legal disclaimers in UI footer, README, and docs

### Definition of Done
- [ ] `git log --all -S "NVIDIA_API_KEY"` returns zero results (secrets purged)
- [ ] `pytest --cov=backend --cov-fail-under=80` passes (test coverage met)
- [ ] GitHub Actions CI passes on push to main
- [ ] `curl http://localhost:8000/openapi.json | jq '.paths | keys | length'` returns >= 10
- [ ] VitePress site builds without errors (`npm run docs:build`)
- [ ] README contains >= 5 images/GIFs and all required sections
- [ ] Zero LSP type errors in backend Python files
- [ ] All 22 tasks have passing acceptance criteria

### Must Have
- Git history purged of all secrets BEFORE any other public-facing work
- MIT LICENSE file at repo root
- CI/CD pipeline blocking merge on test failure
- Legal disclaimer visible on every page of the app
- At least 5 competitive comparison axes in the table
- Architecture diagram in README

### Must NOT Have (Guardrails)
- **MUST NOT** modify the core RAG pipeline logic (retrieval + reranking) — it's a key differentiator, bug fixes only
- **MUST NOT** add user authentication/accounts in V1
- **MUST NOT** add multi-user collaboration features
- **MUST NOT** build mobile apps
- **MUST NOT** add blockchain/web3 features
- **MUST NOT** internationalize beyond Indonesia
- **MUST NOT** add real-time regulatory feeds (defer to post-launch)
- **MUST NOT** build custom LLM fine-tuning pipelines
- **MUST NOT** create SDK packages (npm/PyPI) in V1
- **MUST NOT** break existing UI design, layout, color scheme, or user flows when adding new features

---

## Verification Strategy

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> Every criterion MUST be verifiable by running a command or using a tool.

### Test Decision
- **Infrastructure exists**: YES (Pytest in `tests/test_retriever.py`)
- **Automated tests**: TDD — write tests FIRST for all new work
- **Framework**: Pytest (backend) + React Testing Library / Vitest (frontend)
- **Coverage target**: >80% backend, component-level frontend
- **LLM testing strategy**: Fuzzy matching for citations, separate retrieval-only tests from generation tests
- **CI enforcement**: GitHub Actions blocks merge on test failure

### TDD Workflow (Per Feature Task)

Each feature TODO follows RED-GREEN-REFACTOR:

1. **RED**: Write failing test first
   - Test file: `tests/test_{feature}.py` or `frontend/src/__tests__/{feature}.test.tsx`
   - Test command: `pytest tests/test_{feature}.py` or `npx vitest run src/__tests__/{feature}.test.tsx`
   - Expected: FAIL (test exists, implementation doesn't)
2. **GREEN**: Implement minimum code to pass
   - Expected: PASS
3. **REFACTOR**: Clean up while keeping green
   - Expected: PASS (still)

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

Every task includes QA scenarios executed by the agent via tools:

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| **Frontend/UI** | Playwright (playwright skill) | Navigate, interact, assert DOM, screenshot |
| **Backend/API** | Bash (curl) | Send requests, parse responses, assert fields |
| **CLI/Config** | Bash (shell commands) | Run commands, validate output |
| **Docs Site** | Bash + Playwright | Build check + visual verification |

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 — Security & Foundations (BLOCKER — nothing else starts until done):
└── Task 1: Purge .env from git history + rotate API key

Wave 2 — OSS Infrastructure (after Wave 1):
├── Task 2: Add LICENSE, CODE_OF_CONDUCT, SECURITY.md, legal disclaimers
├── Task 3: Create .github/ templates (issues, PRs)
└── Task 4: Set up CI/CD (GitHub Actions) + test infrastructure

Wave 3 — Code Quality & Existing Tests (after Wave 2):
├── Task 5: Fix all LSP/type errors in backend
├── Task 6: Expand test suite for existing code (retriever, rag_chain, main)
├── Task 7: Set up frontend testing (Vitest + React Testing Library)
└── Task 8: Add rate limiting to API endpoints

Wave 4 — API & Data Layer (after Wave 3):
├── Task 9: API-first design (OpenAPI enhancement, versioning, docs)
├── Task 10: Knowledge Graph — schema design + data model
└── Task 11: Knowledge Graph — data ingestion (build graph from legal docs)

Wave 5 — Core Features (after Wave 4):
├── Task 12: Knowledge Graph — API endpoints + frontend navigation UI
├── Task 13: Multi-turn chat — backend (session management, context window)
└── Task 14: Multi-turn chat — frontend (chat history UI, follow-ups)

Wave 6 — Dashboard & Visualization (after Wave 5):
├── Task 15: Visual Compliance Dashboard — backend (coverage metrics computation)
└── Task 16: Visual Compliance Dashboard — frontend (Recharts heat map)

Wave 7 — Documentation & Presentation (after Wave 6):
├── Task 17: VitePress documentation site (5+ pages, deploy to GitHub Pages)
├── Task 18: README full transformation (showcase design, badges, architecture)
└── Task 19: Competitive comparison table (research + create)

Wave 8 — Launch Readiness (after Wave 7):
├── Task 20: Demo screenshots/GIFs (capture all features)
├── Task 21: CONTRIBUTING.md + "Good First Issues" creation
└── Task 22: Final integration test + launch checklist verification
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|-----------|--------|---------------------|
| 1 | None | ALL | None (critical blocker) |
| 2 | 1 | 5-22 | 3, 4 |
| 3 | 1 | 21 | 2, 4 |
| 4 | 1 | 5-22 | 2, 3 |
| 5 | 2, 4 | 9-22 | 6, 7, 8 |
| 6 | 4 | 9-22 | 5, 7, 8 |
| 7 | 4 | 14, 16 | 5, 6, 8 |
| 8 | 4 | 9 | 5, 6, 7 |
| 9 | 5, 8 | 12, 13 | 10 |
| 10 | 5 | 11 | 9 |
| 11 | 10 | 12, 15 | 9 |
| 12 | 9, 11 | 15 | 13 |
| 13 | 9 | 14 | 12 |
| 14 | 7, 13 | 16 | 12 |
| 15 | 11, 12 | 16 | 13, 14 |
| 16 | 7, 15 | 17 | 14 |
| 17 | 16 | 20 | 18, 19 |
| 18 | 16 | 20 | 17, 19 |
| 19 | 16 | 20 | 17, 18 |
| 20 | 17, 18, 19 | 22 | 21 |
| 21 | 3 | 22 | 20 |
| 22 | 20, 21 | None | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1 | `task(category="deep", load_skills=["git-master"])` |
| 2 | 2, 3, 4 | 3x parallel `task(category="quick", load_skills=["git-master"])` |
| 3 | 5, 6, 7, 8 | 4x parallel `task(category="unspecified-high")` |
| 4 | 9, 10, 11 | `task(category="ultrabrain")` + 2x `task(category="deep")` |
| 5 | 12, 13, 14 | `task(category="visual-engineering", load_skills=["frontend-ui-ux"])` + 2x `task(category="unspecified-high")` |
| 6 | 15, 16 | `task(category="unspecified-high")` + `task(category="visual-engineering", load_skills=["frontend-ui-ux"])` |
| 7 | 17, 18, 19 | 3x parallel: `task(category="writing")` + `task(category="visual-engineering")` + `task(category="quick")` |
| 8 | 20, 21, 22 | `task(category="quick", load_skills=["playwright"])` + `task(category="writing")` + `task(category="deep")` |

---

## TODOs

### Wave 1 — Security (BLOCKER)

- [ ] 1. Purge `.env` from Git History & Harden Secrets

  **What to do**:
  - Install `git-filter-repo` (pip install git-filter-repo) or use BFG Repo-Cleaner
  - Purge `.env` from ALL git history: `git filter-repo --path .env --invert-paths`
  - Force push the cleaned history
  - Update `.gitignore` to explicitly include `.env` (not just `.env*.local`)
  - Create `.env.example` with placeholder values (no real secrets):
    ```
    NVIDIA_API_KEY=your_nvidia_api_key_here
    QDRANT_URL=http://localhost:6333
    QDRANT_API_KEY=your_qdrant_api_key_here
    ```
  - Add a pre-commit hook (`pre-commit` framework) that scans for secrets (using `detect-secrets` or `gitleaks`)
  - Rotate the exposed NVIDIA API key immediately after purge
  - Add `.env` to a `SECURITY.md` advisory if the repo was ever public

  **Must NOT do**:
  - Do NOT simply delete `.env` and commit — it remains in git history
  - Do NOT skip API key rotation — the key is compromised
  - Do NOT modify any application code in this task

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Git history manipulation requires careful, irreversible operations with full understanding of consequences
  - **Skills**: [`git-master`]
    - `git-master`: Direct domain overlap — git filter-repo, force push, history rewriting
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (solo — BLOCKER)
  - **Blocks**: Tasks 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22
  - **Blocked By**: None (first task)

  **References**:

  **Pattern References**:
  - `.env` (root) — The file containing the live NVIDIA API key that must be purged
  - `.gitignore` (root) — Currently only ignores `.env*.local`, must add `.env`

  **Documentation References**:
  - `README.md` — References environment variables setup
  - `DEPLOYMENT.md` — References env var configuration for cloud deployment

  **External References**:
  - Official docs: `https://github.com/newren/git-filter-repo` — git-filter-repo usage
  - Official docs: `https://rtyley.github.io/bfg-repo-cleaner/` — BFG alternative
  - Official docs: `https://pre-commit.com/` — pre-commit hook framework
  - Official docs: `https://github.com/Yelp/detect-secrets` — secret detection tool

  **WHY Each Reference Matters**:
  - `.env`: This is the source of the security vulnerability — contains `NVIDIA_API_KEY`
  - `.gitignore`: Must be updated to prevent `.env` from ever being tracked again
  - `git-filter-repo`: The recommended tool (by GitHub) for rewriting git history safely

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify .env is purged from ALL git history
    Tool: Bash
    Preconditions: git-filter-repo or BFG installed
    Steps:
      1. Run: git log --all --full-history -- .env
      2. Assert: Output is EMPTY (zero commits reference .env)
      3. Run: git log --all -S "NVIDIA_API_KEY" --oneline
      4. Assert: Output is EMPTY (key string not in any commit)
    Expected Result: Zero traces of .env or API key in history
    Evidence: Command output captured

  Scenario: Verify .gitignore blocks .env
    Tool: Bash
    Preconditions: .gitignore updated
    Steps:
      1. Run: cat .gitignore | grep "^\.env$"
      2. Assert: Match found (`.env` is explicitly listed)
      3. Run: touch .env && git status --porcelain | grep ".env"
      4. Assert: .env does NOT appear in git status (ignored)
    Expected Result: .env is properly gitignored
    Evidence: Command output captured

  Scenario: Verify .env.example exists with placeholders
    Tool: Bash
    Preconditions: .env.example created
    Steps:
      1. Run: cat .env.example
      2. Assert: Contains "NVIDIA_API_KEY=your_nvidia_api_key_here"
      3. Assert: Does NOT contain any real API key values
      4. Run: grep -c "your_" .env.example
      5. Assert: Returns >= 2 (multiple placeholder values)
    Expected Result: .env.example has safe placeholder values only
    Evidence: File content captured

  Scenario: Verify pre-commit hook catches secrets
    Tool: Bash
    Preconditions: pre-commit framework installed with detect-secrets
    Steps:
      1. Run: echo "NVIDIA_API_KEY=sk-real-key-12345" > test-secret.txt
      2. Run: git add test-secret.txt
      3. Run: git commit -m "test" (should be blocked by hook)
      4. Assert: Commit is REJECTED with secret detection warning
      5. Run: rm test-secret.txt && git reset HEAD
    Expected Result: Pre-commit hook blocks secret commits
    Evidence: Hook output captured
  ```

  **Evidence to Capture:**
  - [ ] Terminal output of `git log --all -S "NVIDIA_API_KEY"` showing zero results
  - [ ] `.gitignore` content showing `.env` entry
  - [ ] `.env.example` content showing safe placeholders
  - [ ] Pre-commit hook rejection output

  **Commit**: YES
  - Message: `security: purge .env from git history and add secret detection`
  - Files: `.gitignore`, `.env.example`, `.pre-commit-config.yaml`
  - Pre-commit: N/A (this IS the security task)

---

### Wave 2 — OSS Infrastructure

- [ ] 2. Add LICENSE, CODE_OF_CONDUCT, SECURITY.md, Legal Disclaimers

  **What to do**:
  - Create `LICENSE` file at repo root with full MIT license text (use current year, author name from git config)
  - Create `CODE_OF_CONDUCT.md` using Contributor Covenant v2.1 template
  - Create `SECURITY.md` with:
    - Supported versions table
    - Vulnerability reporting process (email-based, NOT public issues)
    - Responsible disclosure timeline (90 days)
    - Known past security issues (mention the .env purge)
  - Add legal disclaimer to:
    - `frontend/`: Footer component of every page: "This tool provides informational guidance only and does not constitute legal advice. Consult a qualified attorney for legal matters."
    - `README.md`: Prominent disclaimer section near the top
  - Remove the text-only "MIT" mention from README and replace with badge linking to LICENSE file

  **Must NOT do**:
  - Do NOT modify any application logic
  - Do NOT change existing UI layout/colors — disclaimer goes in footer only
  - Do NOT use AGPL or any non-MIT license

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Template-based files with minimal customization needed
  - **Skills**: [`git-master`]
    - `git-master`: Needed for clean commit of multiple new files
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Footer disclaimer is minimal text addition, no design work

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 4)
  - **Blocks**: Tasks 5-22
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `README.md` (root) — Currently mentions "MIT" as license but no actual LICENSE file exists. Find the mention and replace with badge.
  - `frontend/` — Locate the layout or footer component to add legal disclaimer text

  **External References**:
  - Official docs: `https://choosealicense.com/licenses/mit/` — Full MIT license template
  - Official docs: `https://www.contributor-covenant.org/version/2/1/code_of_conduct/` — Contributor Covenant v2.1
  - Example: `https://github.com/supabase/supabase/blob/master/SECURITY.md` — Supabase's security policy as reference

  **WHY Each Reference Matters**:
  - `README.md`: Must update the license reference from plain text to badge linking to LICENSE file
  - Frontend layout: Must add disclaimer footer without breaking existing design
  - Contributor Covenant: Industry standard, signals inclusive community

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify LICENSE file exists and is valid MIT
    Tool: Bash
    Preconditions: LICENSE file created
    Steps:
      1. Run: test -f LICENSE && echo "EXISTS" || echo "MISSING"
      2. Assert: Output is "EXISTS"
      3. Run: head -1 LICENSE
      4. Assert: Contains "MIT License"
      5. Run: grep -c "Permission is hereby granted" LICENSE
      6. Assert: Returns 1
    Expected Result: Valid MIT license file at repo root
    Evidence: File content captured

  Scenario: Verify CODE_OF_CONDUCT.md exists
    Tool: Bash
    Preconditions: CODE_OF_CONDUCT.md created
    Steps:
      1. Run: test -f CODE_OF_CONDUCT.md && echo "EXISTS"
      2. Assert: Output is "EXISTS"
      3. Run: grep -c "Contributor Covenant" CODE_OF_CONDUCT.md
      4. Assert: Returns >= 1
    Expected Result: Valid Code of Conduct at repo root
    Evidence: File content captured

  Scenario: Verify SECURITY.md has disclosure process
    Tool: Bash
    Preconditions: SECURITY.md created
    Steps:
      1. Run: test -f SECURITY.md && echo "EXISTS"
      2. Assert: Output is "EXISTS"
      3. Run: grep -ci "vulnerability" SECURITY.md
      4. Assert: Returns >= 2 (mentions vulnerability reporting)
      5. Run: grep -ci "disclosure" SECURITY.md
      6. Assert: Returns >= 1
    Expected Result: Security policy with reporting process
    Evidence: File content captured

  Scenario: Verify legal disclaimer in frontend footer
    Tool: Playwright (playwright skill)
    Preconditions: Frontend dev server running on localhost:3000
    Steps:
      1. Navigate to: http://localhost:3000
      2. Scroll to bottom of page
      3. Assert: Footer contains text "does not constitute legal advice"
      4. Screenshot: .sisyphus/evidence/task-2-disclaimer-footer.png
    Expected Result: Legal disclaimer visible in app footer
    Evidence: .sisyphus/evidence/task-2-disclaimer-footer.png
  ```

  **Commit**: YES
  - Message: `docs: add LICENSE, CODE_OF_CONDUCT, SECURITY.md, and legal disclaimers`
  - Files: `LICENSE`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `frontend/src/...` (footer component)
  - Pre-commit: N/A

---

- [ ] 3. Create `.github/` Issue & PR Templates

  **What to do**:
  - Create `.github/ISSUE_TEMPLATE/bug_report.md` with structured bug report form:
    - Description, steps to reproduce, expected behavior, actual behavior, environment
  - Create `.github/ISSUE_TEMPLATE/feature_request.md` with:
    - Problem description, proposed solution, alternatives considered
  - Create `.github/ISSUE_TEMPLATE/good_first_issue.md` with:
    - Description, files to modify, how to fix, acceptance criteria, estimated time
  - Create `.github/PULL_REQUEST_TEMPLATE.md` with:
    - Summary of changes, type of change (bug fix/feature/etc), testing done, checklist
  - Create `.github/ISSUE_TEMPLATE/config.yml` to optionally link to docs for questions

  **Must NOT do**:
  - Do NOT add complex GitHub Actions in this task (that's Task 4)
  - Do NOT add CODEOWNERS file (not enough contributors yet)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Template files with well-known structure, minimal customization
  - **Skills**: [`git-master`]
    - `git-master`: Creating files in .github/ directory structure
  - **Skills Evaluated but Omitted**:
    - `writing`: Templates are structured forms, not prose

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 4)
  - **Blocks**: Task 21 (CONTRIBUTING.md references these templates)
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - Example: `https://github.com/supabase/supabase/tree/master/.github` — Supabase's GitHub templates
  - Example: `https://github.com/calcom/cal.com/tree/main/.github` — Cal.com's GitHub templates
  - Official docs: `https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests` — GitHub template docs

  **WHY Each Reference Matters**:
  - Supabase/Cal.com templates: Real-world examples of effective issue/PR templates from top OSS projects
  - GitHub docs: Ensure correct YAML structure for `config.yml`

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify all template files exist
    Tool: Bash
    Preconditions: .github/ directory created
    Steps:
      1. Run: test -f .github/ISSUE_TEMPLATE/bug_report.md && echo "OK"
      2. Assert: Output is "OK"
      3. Run: test -f .github/ISSUE_TEMPLATE/feature_request.md && echo "OK"
      4. Assert: Output is "OK"
      5. Run: test -f .github/ISSUE_TEMPLATE/good_first_issue.md && echo "OK"
      6. Assert: Output is "OK"
      7. Run: test -f .github/PULL_REQUEST_TEMPLATE.md && echo "OK"
      8. Assert: Output is "OK"
    Expected Result: All 4 template files exist in correct locations
    Evidence: Command output captured

  Scenario: Verify bug report template has required sections
    Tool: Bash
    Preconditions: bug_report.md exists
    Steps:
      1. Run: grep -c "## " .github/ISSUE_TEMPLATE/bug_report.md
      2. Assert: Returns >= 3 (at least 3 sections)
      3. Run: grep -ci "steps to reproduce" .github/ISSUE_TEMPLATE/bug_report.md
      4. Assert: Returns >= 1
    Expected Result: Bug report has structured sections
    Evidence: File content captured
  ```

  **Commit**: YES (group with Task 2)
  - Message: `chore: add GitHub issue and PR templates`
  - Files: `.github/ISSUE_TEMPLATE/*.md`, `.github/PULL_REQUEST_TEMPLATE.md`
  - Pre-commit: N/A

---

- [ ] 4. Set Up CI/CD Pipeline & Test Infrastructure

  **What to do**:
  - Create `.github/workflows/ci.yml` GitHub Actions workflow:
    - Trigger: push to main, pull_request to main
    - Backend job: Python 3.11, install requirements, run `pytest --cov=backend --cov-fail-under=80`
    - Frontend job: Node 20, install deps, run `npx vitest run` (after Task 7 sets up vitest)
    - Lint job: Python linting (ruff or flake8), TypeScript type check (`tsc --noEmit`)
  - Create `.github/workflows/docs.yml` for VitePress deployment to GitHub Pages (after Task 17)
  - Set up `pytest.ini` or `pyproject.toml` with pytest configuration:
    - Test discovery paths
    - Coverage settings
    - Markers for slow/integration tests
  - Set up Vitest config for frontend (`vitest.config.ts`):
    - Test file patterns
    - React Testing Library setup
    - Coverage configuration
  - Add pytest-cov, pytest-asyncio to `backend/requirements.txt`
  - Add vitest, @testing-library/react, @testing-library/jest-dom to `frontend/package.json` devDependencies
  - Create `backend/conftest.py` with shared fixtures (mock Qdrant client, mock NVIDIA NIM, test data)

  **Must NOT do**:
  - Do NOT write actual test cases here (that's Tasks 6, 7)
  - Do NOT deploy anything — CI is for testing only
  - Do NOT add Docker-based CI (keep it simple with direct installs)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: CI/CD setup requires understanding multiple ecosystems (Python + Node + GitHub Actions)
  - **Skills**: [`git-master`]
    - `git-master`: Understanding workflow files, git hooks integration
  - **Skills Evaluated but Omitted**:
    - `playwright`: Not needed for CI setup (Playwright tests come later)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 3)
  - **Blocks**: Tasks 5, 6, 7, 8 (all testing/quality tasks depend on infrastructure)
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `tests/test_retriever.py` — Existing test file showing current pytest patterns and structure
  - `backend/requirements.txt` — Current Python dependencies (must add test deps here)
  - `frontend/package.json` — Current Node dependencies (must add test devDeps here)
  - `frontend/tsconfig.json` — TypeScript config to reference for `tsc --noEmit` in CI

  **External References**:
  - Official docs: `https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions` — GitHub Actions syntax
  - Official docs: `https://vitest.dev/guide/` — Vitest setup guide
  - Official docs: `https://docs.pytest.org/en/stable/reference/reference.html#ini-options-ref` — pytest configuration
  - Official docs: `https://testing-library.com/docs/react-testing-library/setup` — React Testing Library setup

  **WHY Each Reference Matters**:
  - `test_retriever.py`: Shows existing test patterns so CI config matches current structure
  - `requirements.txt`: Add test dependencies without breaking existing deps
  - Vitest docs: Frontend test framework that works with Next.js + React 19

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify GitHub Actions CI workflow file is valid
    Tool: Bash
    Preconditions: CI workflow file created
    Steps:
      1. Run: test -f .github/workflows/ci.yml && echo "EXISTS"
      2. Assert: Output is "EXISTS"
      3. Run: grep -c "pytest" .github/workflows/ci.yml
      4. Assert: Returns >= 1 (pytest step exists)
      5. Run: grep -c "vitest" .github/workflows/ci.yml
      6. Assert: Returns >= 1 (vitest step exists)
      7. Run: grep -c "tsc" .github/workflows/ci.yml
      8. Assert: Returns >= 1 (type check step exists)
    Expected Result: CI workflow has backend, frontend, and lint jobs
    Evidence: File content captured

  Scenario: Verify pytest runs with existing tests
    Tool: Bash
    Preconditions: pytest and pytest-cov installed
    Steps:
      1. Run: pip install -r backend/requirements.txt
      2. Run: pytest tests/ -v --tb=short
      3. Assert: Exit code 0 (existing tests still pass)
      4. Run: pytest tests/ --cov=backend --cov-report=term
      5. Assert: Coverage report generated (shows percentage)
    Expected Result: Existing tests pass, coverage reporting works
    Evidence: Test output + coverage report captured

  Scenario: Verify conftest.py has mock fixtures
    Tool: Bash
    Preconditions: conftest.py created
    Steps:
      1. Run: test -f backend/conftest.py && echo "EXISTS"
      2. Assert: Output is "EXISTS"
      3. Run: grep -c "@pytest.fixture" backend/conftest.py
      4. Assert: Returns >= 2 (at least 2 fixtures defined)
    Expected Result: Shared test fixtures available
    Evidence: File content captured
  ```

  **Commit**: YES
  - Message: `ci: add GitHub Actions CI/CD pipeline and test infrastructure`
  - Files: `.github/workflows/ci.yml`, `pytest.ini` or `pyproject.toml`, `frontend/vitest.config.ts`, `backend/conftest.py`, `backend/requirements.txt`, `frontend/package.json`
  - Pre-commit: `pytest tests/ -v`

---

### Wave 3 — Code Quality & Testing

- [ ] 5. Fix All LSP/Type Errors in Backend

  **What to do**:
  - Fix all type errors in `backend/main.py`:
    - Line 339: Fix `qdrant_client` attribute access on `HybridRetriever` — add proper type annotation or attribute
    - Line 498: Fix `query_stream` being `None` — add proper None check or type narrowing
    - Line 509: Fix `float` assigned to `dict` parameter — correct the data structure type
  - Fix all type errors in `backend/retriever.py`:
    - Line 159: Fix `int | None` passed to `scroll()` `limit` param — add default value or assert
    - Lines 172-176: Fix `.get()` and `.items()` on `None` — add None checks for payload
    - Line 317: Fix `ExtendedPointId` vs `int` type mismatch — use proper type casting
    - Lines 318-323: Fix `.get()` on `None` payload — add None guards
  - Run `pyright` or `mypy` to verify zero type errors after fixes
  - Ensure all fixes are backward-compatible (no behavior changes)

  **Must NOT do**:
  - Do NOT change the RAG pipeline logic or retrieval algorithms
  - Do NOT refactor code structure — only fix types
  - Do NOT add new features or change function signatures

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding of Python typing, Qdrant SDK types, and FastAPI patterns
  - **Skills**: []
    - No special skills needed — standard Python type fixing
  - **Skills Evaluated but Omitted**:
    - `git-master`: Simple commit, no complex git operations

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 6, 7, 8)
  - **Blocks**: Tasks 9-22 (clean code is prerequisite for new features)
  - **Blocked By**: Tasks 2, 4

  **References**:

  **Pattern References**:
  - `backend/main.py:339` — `qdrant_client` attribute access error on HybridRetriever
  - `backend/main.py:498` — `query_stream` is None type error
  - `backend/main.py:509` — Float vs dict type mismatch in `__setitem__`
  - `backend/retriever.py:159` — `int | None` vs `int` in `scroll()` limit parameter
  - `backend/retriever.py:172-176` — `.get()` and `.items()` called on potential None payload
  - `backend/retriever.py:317-323` — `ExtendedPointId` vs `int` and None payload access

  **API/Type References**:
  - `backend/retriever.py` — `HybridRetriever` class definition (check what attributes it actually has)
  - `backend/rag_chain.py` — `LegalRAGChain` class to understand how main.py calls it

  **WHY Each Reference Matters**:
  - Each line reference is an exact LSP error location — the executor should look at surrounding context to understand the intended behavior before fixing types
  - `retriever.py` class definition: Need to understand if `qdrant_client` should be an attribute or accessed differently

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify zero LSP errors in backend/main.py
    Tool: Bash
    Preconditions: Type fixes applied
    Steps:
      1. Run: pyright backend/main.py 2>&1 | grep -c "error"
      2. Assert: Returns 0 (zero type errors)
    Expected Result: main.py has no type errors
    Evidence: Pyright output captured

  Scenario: Verify zero LSP errors in backend/retriever.py
    Tool: Bash
    Preconditions: Type fixes applied
    Steps:
      1. Run: pyright backend/retriever.py 2>&1 | grep -c "error"
      2. Assert: Returns 0 (zero type errors)
    Expected Result: retriever.py has no type errors
    Evidence: Pyright output captured

  Scenario: Verify existing tests still pass after type fixes
    Tool: Bash
    Preconditions: Type fixes applied, pytest installed
    Steps:
      1. Run: pytest tests/test_retriever.py -v
      2. Assert: Exit code 0 (all tests pass)
      3. Assert: No test failures or errors in output
    Expected Result: Type fixes don't break existing functionality
    Evidence: Test output captured
  ```

  **Commit**: YES
  - Message: `fix: resolve all type errors in backend (main.py, retriever.py)`
  - Files: `backend/main.py`, `backend/retriever.py`
  - Pre-commit: `pytest tests/ -v`

---

- [ ] 6. Expand Backend Test Suite (TDD for Existing Code)

  **What to do**:
  - Write comprehensive tests for `backend/rag_chain.py`:
    - Test `LegalRAGChain._assess_confidence()` with various citation counts
    - Test hallucination risk detection logic
    - Test chain-of-thought prompt construction
    - Test streaming response format
    - Use mocked NVIDIA NIM responses (never call real API in tests)
  - Write comprehensive tests for `backend/main.py` API endpoints:
    - Test `/api/legal-qa` endpoint (POST with valid query, empty query, long query)
    - Test `/api/compliance-check` endpoint (text input + PDF upload)
    - Test `/api/business-guidance` endpoint (PT, CV, UMKM entity types)
    - Test SSE streaming endpoint format
    - Test error handling (invalid input, missing fields, server errors)
    - Use FastAPI TestClient with mocked dependencies
  - Write tests for ingestion scripts in `backend/scripts/`:
    - Test document parsing logic
    - Test tokenization
    - Test data validation
  - Target: >80% coverage on `backend/` directory
  - Use fuzzy matching for LLM-related tests (assert "contains" not "equals")
  - Mark integration tests with `@pytest.mark.integration` (skip in CI by default)

  **Must NOT do**:
  - Do NOT call real NVIDIA NIM API in tests (mock everything)
  - Do NOT call real Qdrant instance in unit tests (use mock client from conftest.py)
  - Do NOT modify application code to make tests pass — only add test files

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Writing comprehensive test suites requires deep understanding of the application logic
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `git-master`: Simple commit, no complex git ops

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 5, 7, 8)
  - **Blocks**: Tasks 9-22
  - **Blocked By**: Task 4 (needs conftest.py fixtures and pytest-cov)

  **References**:

  **Pattern References**:
  - `tests/test_retriever.py` — Existing test patterns (assertions, fixtures, mock strategy)
  - `backend/rag_chain.py` — Core RAG logic to test (confidence scoring, hallucination detection)
  - `backend/main.py` — FastAPI endpoints to test (all route handlers)
  - `backend/scripts/` — Ingestion scripts to test
  - `backend/conftest.py` — Shared fixtures (created in Task 4)

  **API/Type References**:
  - `backend/retriever.py:SearchResult` — Dataclass used in test assertions
  - `backend/rag_chain.py:LegalRAGChain` — Class methods to test

  **External References**:
  - Official docs: `https://fastapi.tiangolo.com/tutorial/testing/` — FastAPI TestClient usage
  - Official docs: `https://docs.pytest.org/en/stable/how-to/fixtures.html` — Pytest fixture patterns

  **WHY Each Reference Matters**:
  - `test_retriever.py`: Follow existing test style for consistency
  - `rag_chain.py`: Core logic where confidence scoring and hallucination detection live — critical to test
  - FastAPI docs: TestClient is the standard way to test FastAPI endpoints without starting a server

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify backend test coverage exceeds 80%
    Tool: Bash
    Preconditions: All test files created, pytest-cov installed
    Steps:
      1. Run: pytest tests/ --cov=backend --cov-fail-under=80 --cov-report=term-missing
      2. Assert: Exit code 0 (coverage threshold met)
      3. Assert: Output shows ">= 80%" total coverage
    Expected Result: Backend coverage is 80% or higher
    Evidence: Coverage report captured

  Scenario: Verify RAG chain tests pass
    Tool: Bash
    Preconditions: test_rag_chain.py created
    Steps:
      1. Run: pytest tests/test_rag_chain.py -v
      2. Assert: Exit code 0
      3. Assert: >= 5 tests passed (confidence, hallucination, prompt, streaming, etc.)
    Expected Result: All RAG chain tests pass
    Evidence: Test output captured

  Scenario: Verify API endpoint tests pass
    Tool: Bash
    Preconditions: test_api.py created
    Steps:
      1. Run: pytest tests/test_api.py -v
      2. Assert: Exit code 0
      3. Assert: >= 8 tests passed (3 endpoints x success+error+edge cases)
    Expected Result: All API tests pass with mocked dependencies
    Evidence: Test output captured
  ```

  **Commit**: YES
  - Message: `test: add comprehensive backend test suite (>80% coverage)`
  - Files: `tests/test_rag_chain.py`, `tests/test_api.py`, `tests/test_scripts.py`
  - Pre-commit: `pytest tests/ --cov=backend --cov-fail-under=80`

---

- [ ] 7. Set Up Frontend Testing (Vitest + React Testing Library)

  **What to do**:
  - Configure Vitest with React Testing Library (setup file, test environment)
  - Write component tests for key frontend components:
    - Legal Q&A form component (input, submit, result display)
    - Compliance Checker form (text + PDF upload mode)
    - Business Formation guidance component
    - Navigation/layout component
    - Any shared UI components (buttons, cards, etc.)
  - Test that existing UI renders without errors
  - Test form validation (empty inputs, invalid inputs)
  - Test loading states and error states
  - Use snapshot tests sparingly (only for static layout components)

  **Must NOT do**:
  - Do NOT write E2E tests here (that's for Playwright in QA scenarios)
  - Do NOT test API call implementations (mock all API calls)
  - Do NOT change any component code — only add test files

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: React 19 + Next.js 16 testing requires understanding of modern React patterns
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Understanding React component structure and testing patterns
  - **Skills Evaluated but Omitted**:
    - `playwright`: Not for unit tests (Playwright is for E2E in QA scenarios)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 5, 6, 8)
  - **Blocks**: Tasks 14, 16 (frontend features need test infrastructure)
  - **Blocked By**: Task 4 (needs Vitest config)

  **References**:

  **Pattern References**:
  - `frontend/src/` — All React components to identify what needs testing
  - `frontend/package.json` — Current dependencies and scripts
  - `frontend/tsconfig.json` — TypeScript config for test file compatibility
  - `frontend/vitest.config.ts` — Vitest config (created in Task 4)

  **External References**:
  - Official docs: `https://vitest.dev/guide/` — Vitest usage
  - Official docs: `https://testing-library.com/docs/react-testing-library/intro` — RTL patterns
  - Official docs: `https://nextjs.org/docs/app/building-your-application/testing/vitest` — Next.js + Vitest setup

  **WHY Each Reference Matters**:
  - `frontend/src/`: Must examine actual component files to write meaningful tests
  - Next.js + Vitest docs: Specific setup needed for App Router compatibility

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify frontend tests run successfully
    Tool: Bash
    Preconditions: Vitest configured, test files created
    Steps:
      1. Run: cd frontend && npx vitest run --reporter=verbose 2>&1
      2. Assert: Exit code 0 (all tests pass)
      3. Assert: >= 10 tests passed
    Expected Result: Frontend component tests pass
    Evidence: Test output captured
  ```

  **Commit**: YES
  - Message: `test: add frontend component tests with Vitest + React Testing Library`
  - Files: `frontend/src/__tests__/*.test.tsx`, `frontend/vitest.setup.ts`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [ ] 8. Add API Rate Limiting

  **What to do**:
  - Install `slowapi` (or `fastapi-limiter`) in backend
  - Add rate limiting to all public API endpoints:
    - `/api/legal-qa`: 20 requests/minute per IP
    - `/api/compliance-check`: 10 requests/minute per IP (heavier processing)
    - `/api/business-guidance`: 20 requests/minute per IP
  - Return proper `429 Too Many Requests` response with `Retry-After` header
  - Add rate limit headers to all responses: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
  - Write tests for rate limiting behavior
  - Add rate limiting documentation to API docs (in code docstrings)

  **Must NOT do**:
  - Do NOT add authentication/API keys (V1 is public)
  - Do NOT add per-user rate limiting (no user accounts yet)
  - Do NOT add Redis dependency (use in-memory rate limiting for simplicity)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Rate limiting integration with FastAPI requires understanding middleware patterns
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Backend-only task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 5, 6, 7)
  - **Blocks**: Task 9 (API-first design builds on rate-limited endpoints)
  - **Blocked By**: Task 4

  **References**:

  **Pattern References**:
  - `backend/main.py` — All FastAPI route handlers that need rate limit decorators

  **External References**:
  - Official docs: `https://slowapi.readthedocs.io/en/latest/` — SlowAPI for FastAPI
  - Official docs: `https://fastapi.tiangolo.com/advanced/middleware/` — FastAPI middleware patterns

  **WHY Each Reference Matters**:
  - `main.py`: Must identify all route handlers to apply rate limit decorators
  - SlowAPI docs: The library that adds rate limiting with minimal code changes

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify rate limiting returns 429 on excess requests
    Tool: Bash
    Preconditions: Backend running with rate limiting enabled
    Steps:
      1. Run: for i in $(seq 1 25); do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/legal-qa -H "Content-Type: application/json" -d '{"query":"test"}'; done
      2. Assert: First 20 responses are 200 (or other success codes)
      3. Assert: Responses after 20 are 429 (rate limited)
    Expected Result: Rate limiting kicks in after threshold
    Evidence: HTTP status codes captured

  Scenario: Verify rate limit headers in responses
    Tool: Bash
    Preconditions: Backend running
    Steps:
      1. Run: curl -s -D - -X POST http://localhost:8000/api/legal-qa -H "Content-Type: application/json" -d '{"query":"test"}' 2>&1 | grep -i "x-ratelimit"
      2. Assert: Contains X-RateLimit-Limit header
      3. Assert: Contains X-RateLimit-Remaining header
    Expected Result: Rate limit headers present in responses
    Evidence: Response headers captured
  ```

  **Commit**: YES
  - Message: `feat: add API rate limiting with slowapi (20 req/min per IP)`
  - Files: `backend/main.py`, `backend/requirements.txt`, `tests/test_rate_limit.py`
  - Pre-commit: `pytest tests/ -v`

### Wave 4 — API & Data Layer

- [ ] 9. API-First Design (OpenAPI Enhancement & Versioning)

  **What to do**:
  - Restructure FastAPI routes with `/api/v1/` prefix for versioning
  - Enhance all existing endpoint docstrings with:
    - Detailed descriptions (what the endpoint does, when to use it)
    - Request/response model examples using Pydantic `model_config` with `json_schema_extra`
    - Error response schemas (400, 404, 422, 429, 500)
  - Create Pydantic response models for ALL endpoints (currently may return raw dicts):
    - `LegalQAResponse`: answer, citations, confidence_score, hallucination_risk
    - `ComplianceCheckResponse`: analysis, risks, recommendations
    - `BusinessGuidanceResponse`: steps, requirements, timeline
  - Add OpenAPI metadata to FastAPI app:
    - Title: "Omnibus Legal Compass API"
    - Description with markdown formatting
    - Version: "1.0.0"
    - Contact info, license info
    - Tags for endpoint grouping (Legal QA, Compliance, Business, Health)
  - Add `/api/v1/health` endpoint (returns status, version, uptime)
  - Ensure `/docs` (Swagger UI) and `/redoc` (ReDoc) are accessible
  - Write TDD tests for all new/modified endpoints

  **Must NOT do**:
  - Do NOT add authentication middleware (public API for V1)
  - Do NOT create separate SDK packages
  - Do NOT change the internal RAG logic — only restructure the API layer
  - Do NOT break existing frontend API calls (maintain backward compatibility or update frontend simultaneously)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: API versioning + backward compatibility + Pydantic model design requires careful architectural thinking
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Frontend URL updates are mechanical, not design work

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 10, 11)
  - **Blocks**: Tasks 12, 13 (new features use versioned API)
  - **Blocked By**: Tasks 5, 8 (clean code + rate limiting in place)

  **References**:

  **Pattern References**:
  - `backend/main.py` — All current FastAPI route handlers (must preserve behavior while restructuring)
  - `backend/rag_chain.py` — Return types from RAG chain (shapes the response models)
  - `backend/retriever.py:SearchResult` — Existing dataclass pattern to follow for response models
  - `frontend/src/` — Frontend API call patterns (must update URLs from `/api/` to `/api/v1/`)

  **External References**:
  - Official docs: `https://fastapi.tiangolo.com/tutorial/metadata/` — FastAPI metadata and tags
  - Official docs: `https://fastapi.tiangolo.com/tutorial/response-model/` — Response model patterns
  - Example: `https://github.com/tiangolo/full-stack-fastapi-template` — FastAPI project structure reference

  **WHY Each Reference Matters**:
  - `main.py`: Must understand all existing routes to restructure without breaking
  - `rag_chain.py`: Return values shape the Pydantic response models
  - Frontend: Must update API base URL to `/api/v1/` to maintain functionality

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify OpenAPI spec is valid and comprehensive
    Tool: Bash
    Preconditions: Backend running with new API structure
    Steps:
      1. Run: curl -s http://localhost:8000/openapi.json | python -m json.tool > /dev/null
      2. Assert: Exit code 0 (valid JSON)
      3. Run: curl -s http://localhost:8000/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print(len(d['paths']))"
      4. Assert: Returns >= 5 (at least 5 endpoints documented)
      5. Run: curl -s http://localhost:8000/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print(d['info']['title'])"
      6. Assert: Contains "Omnibus Legal Compass"
    Expected Result: Complete, valid OpenAPI spec with project metadata
    Evidence: OpenAPI JSON captured

  Scenario: Verify /api/v1/ versioned endpoints work
    Tool: Bash
    Preconditions: Backend running
    Steps:
      1. Run: curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health
      2. Assert: Returns 200
      3. Run: curl -s http://localhost:8000/api/v1/health | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('version','MISSING'))"
      4. Assert: Returns "1.0.0"
    Expected Result: Versioned API with health endpoint
    Evidence: Response captured

  Scenario: Verify Swagger UI is accessible
    Tool: Playwright (playwright skill)
    Preconditions: Backend running
    Steps:
      1. Navigate to: http://localhost:8000/docs
      2. Wait for: .swagger-ui visible (timeout: 10s)
      3. Assert: Page title contains "Omnibus Legal Compass"
      4. Screenshot: .sisyphus/evidence/task-9-swagger-ui.png
    Expected Result: Interactive API documentation loads
    Evidence: .sisyphus/evidence/task-9-swagger-ui.png
  ```

  **Commit**: YES
  - Message: `feat: API v1 versioning with enhanced OpenAPI documentation`
  - Files: `backend/main.py`, `backend/models/`, `frontend/src/` (API URL updates), `tests/test_api_v1.py`
  - Pre-commit: `pytest tests/ -v`

---

- [ ] 10. Knowledge Graph — Schema Design & Data Model

  **What to do**:
  - Design the Knowledge Graph schema with these node types:
    - **Law** (UU/Undang-Undang): id, number, year, title, status (active/amended/repealed), enactment_date
    - **GovernmentRegulation** (PP/Peraturan Pemerintah): id, number, year, title, parent_law_id
    - **PresidentialRegulation** (Perpres): id, number, year, title, parent_law_id
    - **MinisterialRegulation** (Permen): id, number, year, title, issuing_ministry
    - **Chapter** (Bab): id, number, title, parent_law_id
    - **Article** (Pasal): id, number, content_summary, full_text, parent_chapter_id
  - Design edge types:
    - `CONTAINS`: Law → Chapter → Article (hierarchy)
    - `IMPLEMENTS`: PP/Perpres → Law (implementing regulation)
    - `AMENDS`: Law → Law (amendment relationship, with effective_date)
    - `REFERENCES`: Article → Article (cross-reference)
    - `SUPERSEDES`: Law → Law (with supersession_date)
  - Choose graph storage approach:
    - Option A: NetworkX (in-memory, good for moderate size) with JSON serialization
    - Option B: Neo4j (if data is large, but adds infrastructure dependency)
    - Recommended: NetworkX for V1 (fits 5,817 documents, no extra DB needed)
  - Create Python data models (Pydantic) for all node/edge types
  - Create `backend/knowledge_graph/` module:
    - `schema.py`: All Pydantic models for nodes and edges
    - `graph.py`: Graph class with query methods
    - `__init__.py`: Public API
  - Write TDD tests for schema validation and graph operations
  - Design API endpoints (implementation in Task 12):
    - `GET /api/v1/graph/laws` — List all laws with status
    - `GET /api/v1/graph/law/{id}` — Get law with chapters and articles
    - `GET /api/v1/graph/law/{id}/hierarchy` — Get full regulation hierarchy
    - `GET /api/v1/graph/article/{id}/references` — Get cross-references
    - `GET /api/v1/graph/search?q=...` — Search graph by text

  **Must NOT do**:
  - Do NOT ingest data in this task (that's Task 11)
  - Do NOT build frontend UI (that's Task 12)
  - Do NOT add Neo4j as a dependency unless NetworkX proves insufficient
  - Do NOT over-engineer the temporal versioning — simple "active/amended/repealed" status + amendment edges is sufficient

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Schema design for legal ontology requires careful domain modeling and understanding of Indonesian legal hierarchy
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Backend-only schema task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 9, 11)
  - **Blocks**: Task 11 (ingestion needs schema), Task 12 (API needs schema)
  - **Blocked By**: Task 5 (clean backend code)

  **References**:

  **Pattern References**:
  - `backend/retriever.py:SearchResult` — Existing Pydantic/dataclass pattern to follow
  - `data/DATA_SCHEMA.md` — Schema of the 5,817 legal documents (field names, citation formats like `UU No. 11 Tahun 2020, Pasal 5`)
  - `data/` — Sample legal JSON documents showing actual data structure
  - `backend/scripts/` — Ingestion scripts that parse legal documents (understand source data format)

  **Documentation References**:
  - `data/DATA_SCHEMA.md` — Field definitions for legal documents

  **External References**:
  - Official docs: `https://networkx.org/documentation/stable/tutorial.html` — NetworkX graph basics
  - Official docs: `https://docs.pydantic.dev/latest/` — Pydantic model patterns
  - Reference: Indonesian legal hierarchy structure (UU → PP → Perpres → Permen)

  **WHY Each Reference Matters**:
  - `DATA_SCHEMA.md`: Critical — defines the actual field names and data structure of source documents
  - `data/`: Sample documents to understand what fields exist (title, article numbers, chapter structure)
  - `scripts/`: Shows how documents are currently parsed — schema must align with existing data

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify Knowledge Graph schema models are valid
    Tool: Bash
    Preconditions: schema.py created with Pydantic models
    Steps:
      1. Run: python -c "from backend.knowledge_graph.schema import Law, Chapter, Article; print('IMPORTS OK')"
      2. Assert: Output is "IMPORTS OK"
      3. Run: python -c "from backend.knowledge_graph.schema import Law; l = Law(id='uu-11-2020', number=11, year=2020, title='Cipta Kerja', status='active', enactment_date='2020-11-02'); print(l.model_dump_json())"
      4. Assert: Valid JSON output with all fields
    Expected Result: All schema models importable and validatable
    Evidence: Python output captured

  Scenario: Verify graph operations work
    Tool: Bash
    Preconditions: graph.py created
    Steps:
      1. Run: pytest tests/test_knowledge_graph.py -v
      2. Assert: Exit code 0
      3. Assert: Tests for add_law, add_chapter, add_article, get_hierarchy, get_references all pass
    Expected Result: Graph CRUD and query operations work
    Evidence: Test output captured
  ```

  **Commit**: YES
  - Message: `feat: knowledge graph schema design with Pydantic models and NetworkX`
  - Files: `backend/knowledge_graph/__init__.py`, `backend/knowledge_graph/schema.py`, `backend/knowledge_graph/graph.py`, `tests/test_knowledge_graph.py`
  - Pre-commit: `pytest tests/test_knowledge_graph.py -v`

---

- [ ] 11. Knowledge Graph — Data Ingestion (Build Graph from Legal Docs)

  **What to do**:
  - Create `backend/knowledge_graph/ingest.py`:
    - Parse existing legal JSON documents from `data/` directory
    - Extract law metadata (number, year, title, status)
    - Extract chapter structure (Bab numbers and titles)
    - Extract article content (Pasal numbers, text)
    - Identify cross-references between articles (regex patterns like "sebagaimana dimaksud dalam Pasal X")
    - Identify amendment relationships (patterns like "mengubah UU Nomor X Tahun Y")
    - Build hierarchical relationships (UU → PP → Perpres based on metadata)
  - Create `backend/knowledge_graph/persistence.py`:
    - Save graph to JSON file (for loading on server start)
    - Load graph from JSON file
    - Graph file location: `data/knowledge_graph.json`
  - Create ingestion CLI command: `python -m backend.knowledge_graph.ingest`
  - Add graph loading to FastAPI startup event (load once, serve from memory)
  - Write tests for ingestion logic:
    - Test parsing of sample legal documents
    - Test cross-reference detection regex
    - Test amendment relationship extraction
    - Test persistence (save/load round-trip)
  - Add citation validation: verify that referenced articles exist in the graph (detect hallucination-prone references)

  **Must NOT do**:
  - Do NOT scrape external websites for legal documents
  - Do NOT modify existing legal document files
  - Do NOT create a separate database (use JSON file + in-memory NetworkX)
  - Do NOT process documents that aren't in the existing `data/` directory

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: NLP-style parsing of Indonesian legal text, regex patterns for cross-references, domain expertise needed
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Backend-only data processing

  **Parallelization**:
  - **Can Run In Parallel**: YES (partially — needs Task 10 schema first)
  - **Parallel Group**: Wave 4 (starts after Task 10 completes)
  - **Blocks**: Tasks 12, 15 (API and dashboard need populated graph)
  - **Blocked By**: Task 10 (schema must exist first)

  **References**:

  **Pattern References**:
  - `backend/knowledge_graph/schema.py` — Node/edge models (created in Task 10)
  - `data/` — All legal JSON documents to ingest
  - `data/DATA_SCHEMA.md` — Document field definitions and citation format examples
  - `backend/scripts/` — Existing ingestion scripts (may have parsing logic to reuse)
  - `backend/retriever.py` — Indonesian tokenizer and text processing patterns to reuse

  **WHY Each Reference Matters**:
  - `data/DATA_SCHEMA.md`: Shows citation format `Berdasarkan UU No. 11 Tahun 2020, Pasal 5` — needed for cross-reference regex
  - `scripts/`: May contain parsing utilities (tokenizer, text normalization) that should be reused
  - `retriever.py`: Indonesian tokenizer is needed for text processing in graph construction

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify ingestion processes all documents
    Tool: Bash
    Preconditions: Ingestion script created, legal docs in data/
    Steps:
      1. Run: python -m backend.knowledge_graph.ingest 2>&1 | tail -5
      2. Assert: Output shows "Ingested X laws, Y chapters, Z articles"
      3. Assert: X > 0, Y > 0, Z > 0
      4. Run: test -f data/knowledge_graph.json && echo "EXISTS"
      5. Assert: Output is "EXISTS"
    Expected Result: Graph built and persisted to JSON
    Evidence: Ingestion output captured

  Scenario: Verify graph has correct structure
    Tool: Bash
    Preconditions: knowledge_graph.json exists
    Steps:
      1. Run: python -c "import json; g=json.load(open('data/knowledge_graph.json')); print(f'Nodes: {len(g.get(\"nodes\", []))}, Edges: {len(g.get(\"edges\", []))}')"
      2. Assert: Nodes > 100 (meaningful number of laws/chapters/articles)
      3. Assert: Edges > 50 (meaningful relationships)
    Expected Result: Graph has substantial content
    Evidence: Node/edge counts captured

  Scenario: Verify cross-reference detection
    Tool: Bash
    Preconditions: Ingestion complete
    Steps:
      1. Run: pytest tests/test_knowledge_graph_ingest.py -v -k "cross_reference"
      2. Assert: Exit code 0
      3. Assert: Tests verify "sebagaimana dimaksud dalam Pasal" pattern detection
    Expected Result: Cross-references correctly extracted
    Evidence: Test output captured
  ```

  **Commit**: YES
  - Message: `feat: knowledge graph data ingestion from legal documents`
  - Files: `backend/knowledge_graph/ingest.py`, `backend/knowledge_graph/persistence.py`, `data/knowledge_graph.json`, `tests/test_knowledge_graph_ingest.py`
  - Pre-commit: `pytest tests/test_knowledge_graph*.py -v`

---

### Wave 5 — Core Features

- [ ] 12. Knowledge Graph — API Endpoints & Frontend Navigation UI

  **What to do**:
  - **Backend**: Implement Knowledge Graph API endpoints in `backend/main.py`:
    - `GET /api/v1/graph/laws` — List all laws with filters (status, year, type)
    - `GET /api/v1/graph/law/{id}` — Get single law with nested chapters and articles
    - `GET /api/v1/graph/law/{id}/hierarchy` — Get full regulation hierarchy (PP, Perpres, Permen implementing this law)
    - `GET /api/v1/graph/article/{id}/references` — Get cross-references (incoming + outgoing)
    - `GET /api/v1/graph/search?q=...` — Full-text search across graph nodes
    - `GET /api/v1/graph/stats` — Graph statistics (total laws, articles, references, coverage)
  - **Frontend**: Create Knowledge Graph navigation page:
    - New route: `/graph` or `/knowledge-graph`
    - Tree view showing Law → Chapter → Article hierarchy (collapsible)
    - Click article to see full text + cross-references
    - Search bar to filter/find specific laws or articles
    - Visual indicator for law status (active/amended/repealed with color coding)
    - Link from Q&A results to relevant graph nodes (click citation → graph view)
  - Add navigation link to existing app navigation (without changing layout)
  - Write TDD tests for API endpoints + frontend component tests

  **Must NOT do**:
  - Do NOT add a full D3.js/vis.js interactive graph visualization (too complex for V1 — use tree view)
  - Do NOT change existing page layouts or navigation structure — ADD new page alongside
  - Do NOT modify the RAG pipeline

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Frontend tree view + backend API — full-stack task with UI component creation
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Tree view UI component design, color coding for status, navigation integration
  - **Skills Evaluated but Omitted**:
    - `playwright`: QA scenarios use Playwright, but the skill is for task execution guidance

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 13, 14)
  - **Blocks**: Task 15 (dashboard needs graph API)
  - **Blocked By**: Tasks 9, 11 (API structure + populated graph)

  **References**:

  **Pattern References**:
  - `backend/main.py` — Existing endpoint patterns (follow same structure for graph endpoints)
  - `backend/knowledge_graph/graph.py` — Graph query methods (created in Task 10)
  - `frontend/src/` — Existing page structure, layout components, navigation patterns
  - `frontend/src/app/` — Next.js App Router page structure (create new page here)

  **API/Type References**:
  - `backend/knowledge_graph/schema.py` — Pydantic models for graph nodes (response shapes)

  **External References**:
  - Official docs: `https://nextjs.org/docs/app/building-your-application/routing/pages` — App Router page creation

  **WHY Each Reference Matters**:
  - `main.py`: Must follow existing endpoint patterns for consistency
  - `frontend/src/app/`: Must understand routing convention to add new page correctly
  - `schema.py`: Response models are already defined — endpoints return these

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify Knowledge Graph API returns laws
    Tool: Bash
    Preconditions: Backend running with graph loaded
    Steps:
      1. Run: curl -s http://localhost:8000/api/v1/graph/laws | python -c "import json,sys; d=json.load(sys.stdin); print(len(d))"
      2. Assert: Returns > 0 (laws exist)
      3. Run: curl -s http://localhost:8000/api/v1/graph/stats | python -c "import json,sys; d=json.load(sys.stdin); print(d)"
      4. Assert: Shows total_laws, total_articles, total_references
    Expected Result: Graph API returns populated data
    Evidence: API response captured

  Scenario: Verify Knowledge Graph page renders in frontend
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running
    Steps:
      1. Navigate to: http://localhost:3000/knowledge-graph
      2. Wait for: [data-testid="graph-tree"] visible (timeout: 10s)
      3. Assert: Tree view shows at least 1 law node
      4. Click: First law node to expand
      5. Assert: Chapter nodes appear under law
      6. Screenshot: .sisyphus/evidence/task-12-knowledge-graph.png
    Expected Result: Knowledge Graph tree view renders with data
    Evidence: .sisyphus/evidence/task-12-knowledge-graph.png

  Scenario: Verify graph search works
    Tool: Bash
    Preconditions: Backend running with graph
    Steps:
      1. Run: curl -s "http://localhost:8000/api/v1/graph/search?q=cipta%20kerja" | python -c "import json,sys; d=json.load(sys.stdin); print(len(d))"
      2. Assert: Returns > 0 (search finds results)
    Expected Result: Graph search returns matching nodes
    Evidence: API response captured
  ```

  **Commit**: YES
  - Message: `feat: knowledge graph API endpoints and frontend navigation UI`
  - Files: `backend/main.py`, `frontend/src/app/knowledge-graph/page.tsx`, `frontend/src/components/graph/`, `tests/test_graph_api.py`
  - Pre-commit: `pytest tests/ -v`

---

- [ ] 13. Multi-turn Chat — Backend (Session Management & Context Window)

  **What to do**:
  - Create `backend/chat/` module:
    - `session.py`: In-memory session manager using Python dict
      - `create_session() -> session_id` (UUID)
      - `add_message(session_id, role, content)`
      - `get_history(session_id) -> list[Message]` (last 10 messages)
      - `clear_session(session_id)`
      - Session auto-expiry after 30 minutes of inactivity
    - `context.py`: Context window engineering
      - Sliding window: keep last 10 messages
      - Inject chat history into LLM prompt as conversation context
      - Summarize older messages if context exceeds token limit
  - Modify `/api/v1/legal-qa` endpoint to accept optional `session_id`:
    - If no `session_id`: create new session, return `session_id` in response
    - If `session_id` provided: load history, inject context, return answer with same `session_id`
  - Add new endpoints:
    - `GET /api/v1/chat/sessions/{id}` — Get session history
    - `DELETE /api/v1/chat/sessions/{id}` — Clear session
  - Write TDD tests:
    - Test session creation and message storage
    - Test 10-message sliding window (11th message drops oldest)
    - Test auto-expiry (mock time)
    - Test context injection into LLM prompt
    - Test follow-up questions use previous context

  **Must NOT do**:
  - Do NOT persist sessions to database (in-memory only for V1)
  - Do NOT add user accounts or authentication
  - Do NOT share sessions between users
  - Do NOT add WebSocket support (keep HTTP request/response pattern)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Session management, context engineering, and LLM prompt modification require careful state management
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Backend-only task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 12, 14)
  - **Blocks**: Task 14 (frontend needs chat API)
  - **Blocked By**: Task 9 (uses v1 API structure)

  **References**:

  **Pattern References**:
  - `backend/main.py` — Existing `/api/legal-qa` endpoint to modify
  - `backend/rag_chain.py` — LLM prompt construction (must inject history into existing prompt pattern)
  - `backend/rag_chain.py:LegalRAGChain` — System prompt and chain-of-thought pattern (history goes BEFORE the user query)

  **External References**:
  - Official docs: `https://python.langchain.com/docs/how_to/chatbots_memory/` — LangChain memory patterns
  - Official docs: `https://python.langchain.com/docs/how_to/message_history/` — Message history management

  **WHY Each Reference Matters**:
  - `rag_chain.py`: Must understand the existing prompt template to know WHERE to inject conversation history
  - LangChain memory docs: May be able to use LangChain's built-in memory classes instead of custom implementation

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify multi-turn conversation maintains context
    Tool: Bash
    Preconditions: Backend running
    Steps:
      1. Run: SESSION=$(curl -s -X POST http://localhost:8000/api/v1/legal-qa -H "Content-Type: application/json" -d '{"query":"Apa itu UU Cipta Kerja?"}' | python -c "import json,sys; print(json.load(sys.stdin).get('session_id',''))")
      2. Assert: SESSION is not empty (UUID format)
      3. Run: curl -s -X POST http://localhost:8000/api/v1/legal-qa -H "Content-Type: application/json" -d "{\"query\":\"Kapan disahkan?\",\"session_id\":\"$SESSION\"}" | python -c "import json,sys; a=json.load(sys.stdin).get('answer',''); print('2020' in a.lower() or 'november' in a.lower())"
      4. Assert: Returns True (follow-up understands "it" refers to UU Cipta Kerja)
    Expected Result: Second query uses context from first (knows "it" = UU Cipta Kerja)
    Evidence: Both API responses captured

  Scenario: Verify session sliding window (10 message limit)
    Tool: Bash
    Preconditions: Backend running
    Steps:
      1. Run: pytest tests/test_chat.py -v -k "sliding_window"
      2. Assert: Exit code 0
      3. Assert: Test verifies 11th message causes 1st to be dropped
    Expected Result: Sliding window correctly maintains last 10 messages
    Evidence: Test output captured

  Scenario: Verify session auto-expiry
    Tool: Bash
    Preconditions: Backend running
    Steps:
      1. Run: pytest tests/test_chat.py -v -k "auto_expiry"
      2. Assert: Exit code 0
    Expected Result: Sessions expire after 30 minutes of inactivity
    Evidence: Test output captured
  ```

  **Commit**: YES
  - Message: `feat: multi-turn chat with session management and context window`
  - Files: `backend/chat/__init__.py`, `backend/chat/session.py`, `backend/chat/context.py`, `backend/main.py`, `tests/test_chat.py`
  - Pre-commit: `pytest tests/test_chat.py -v`

---

- [ ] 14. Multi-turn Chat — Frontend (Chat History UI & Follow-ups)

  **What to do**:
  - Redesign the Legal Q&A page to support chat-style interaction:
    - Chat message list showing user questions and AI responses (bubble style)
    - Each AI response still shows citations, confidence score, hallucination risk
    - Session indicator (show "Session active" with ability to "Start new conversation")
    - Input field at bottom (like ChatGPT/Claude pattern)
    - Auto-scroll to latest message
    - Loading indicator while waiting for response
  - Store `session_id` in React state (or URL parameter for shareability)
  - Add "Clear conversation" button
  - Show conversation history count ("3/10 messages in context")
  - Ensure existing single-question mode still works (no session_id = fresh query)
  - Add component tests for chat UI
  - Preserve existing design system (colors, fonts, spacing, animations)

  **Must NOT do**:
  - Do NOT change the compliance checker or business guidance pages
  - Do NOT add user accounts or persistent chat history (sessions are ephemeral)
  - Do NOT change the app's color scheme, font system, or animation library
  - Do NOT add markdown rendering for AI responses (unless already present)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Chat UI is a significant frontend component requiring careful UX design
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Chat bubble design, auto-scroll, loading states, message list UX
  - **Skills Evaluated but Omitted**:
    - `playwright`: Used in QA scenarios, not for implementation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 12, 13)
  - **Blocks**: Task 16 (dashboard may reuse chat patterns)
  - **Blocked By**: Tasks 7, 13 (frontend test infra + chat backend)

  **References**:

  **Pattern References**:
  - `frontend/src/` — Existing Legal Q&A page component (the one being redesigned)
  - `frontend/src/` — Design system: Tailwind classes, Framer Motion animations, color palette
  - `frontend/package.json` — Check for existing chat-related dependencies

  **External References**:
  - Official docs: `https://react.dev/learn/updating-arrays-in-state` — React state management for message lists
  - Reference: ChatGPT/Claude UI pattern — message bubbles, auto-scroll, input at bottom

  **WHY Each Reference Matters**:
  - Existing Q&A page: Must understand current UI to preserve design while converting to chat format
  - Tailwind/Framer Motion: Must use existing design system classes, not introduce new styling approach

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify chat UI renders and supports multi-turn
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running
    Steps:
      1. Navigate to: http://localhost:3000 (or the legal Q&A page)
      2. Wait for: input field visible (timeout: 5s)
      3. Fill: Chat input with "Apa itu UU Cipta Kerja?"
      4. Click: Submit button
      5. Wait for: AI response bubble visible (timeout: 30s)
      6. Assert: Response contains citation text
      7. Fill: Chat input with "Kapan disahkan?"
      8. Click: Submit button
      9. Wait for: Second AI response bubble visible (timeout: 30s)
      10. Assert: Page shows 2 user messages + 2 AI responses
      11. Screenshot: .sisyphus/evidence/task-14-chat-multiturn.png
    Expected Result: Multi-turn chat works with visible conversation history
    Evidence: .sisyphus/evidence/task-14-chat-multiturn.png

  Scenario: Verify "New conversation" button clears history
    Tool: Playwright (playwright skill)
    Preconditions: Active chat session with messages
    Steps:
      1. Click: "Start new conversation" button
      2. Assert: Message list is empty
      3. Assert: Input field is focused
      4. Screenshot: .sisyphus/evidence/task-14-chat-clear.png
    Expected Result: Conversation cleared, ready for new session
    Evidence: .sisyphus/evidence/task-14-chat-clear.png
  ```

  **Commit**: YES
  - Message: `feat: multi-turn chat UI with conversation history`
  - Files: `frontend/src/app/` (Q&A page), `frontend/src/components/chat/`, `frontend/src/__tests__/chat.test.tsx`
  - Pre-commit: `cd frontend && npx vitest run`

---

- [ ] 15. Visual Compliance Dashboard — Backend (Coverage Metrics Computation)

  **What to do**:
  - Create `backend/dashboard/` module:
    - `coverage.py`: Compute law coverage metrics
      - For each legal domain (Labor, Tax, Business, Environmental, etc.):
        - Total articles in domain (from Knowledge Graph)
        - Articles indexed in Qdrant (searchable)
        - Coverage percentage = indexed / total
        - Missing articles list
      - For each law:
        - Total chapters and articles
        - Indexed vs missing
        - Last update timestamp
    - `metrics.py`: Aggregate metrics
      - Overall system coverage percentage
      - Per-domain coverage breakdown
      - Most/least covered domains
      - Recent ingestion activity
  - Add API endpoints:
    - `GET /api/v1/dashboard/coverage` — Full coverage data for heat map
    - `GET /api/v1/dashboard/stats` — Aggregate statistics
    - `GET /api/v1/dashboard/coverage/{domain}` — Per-domain detail
  - Cross-reference Knowledge Graph (Task 11 data) with Qdrant index:
    - Query Qdrant to check which articles have embeddings
    - Compare against graph's full article list
    - Identify gaps
  - Write TDD tests for coverage computation

  **Must NOT do**:
  - Do NOT build the frontend visualization (that's Task 16)
  - Do NOT add export functionality (CSV, PDF — defer to post-launch)
  - Do NOT add custom report generation
  - Do NOT modify the Qdrant index structure

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Cross-referencing Knowledge Graph with Qdrant requires understanding both data stores
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Backend-only task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 6 (with Task 16 after this completes)
  - **Blocks**: Task 16 (frontend needs coverage API)
  - **Blocked By**: Tasks 11, 12 (needs populated graph + graph API)

  **References**:

  **Pattern References**:
  - `backend/knowledge_graph/graph.py` — Graph query methods for total article counts
  - `backend/retriever.py` — Qdrant client usage patterns (how to query for indexed articles)
  - `backend/main.py` — Existing endpoint patterns to follow

  **API/Type References**:
  - `backend/knowledge_graph/schema.py` — Node types for domain categorization

  **WHY Each Reference Matters**:
  - `graph.py`: Source for "total articles per domain" computation
  - `retriever.py`: Shows how to query Qdrant — needed to check which articles have embeddings
  - `schema.py`: Node types define what domains/categories exist

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify coverage API returns valid data
    Tool: Bash
    Preconditions: Backend running with graph + Qdrant
    Steps:
      1. Run: curl -s http://localhost:8000/api/v1/dashboard/coverage | python -c "import json,sys; d=json.load(sys.stdin); print(type(d))"
      2. Assert: Returns "<class 'list'>" or "<class 'dict'>" (valid JSON structure)
      3. Run: curl -s http://localhost:8000/api/v1/dashboard/stats | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('overall_coverage_percent', 'MISSING'))"
      4. Assert: Returns a number between 0 and 100
    Expected Result: Coverage API returns meaningful metrics
    Evidence: API responses captured

  Scenario: Verify coverage computation tests pass
    Tool: Bash
    Preconditions: test_dashboard.py created
    Steps:
      1. Run: pytest tests/test_dashboard.py -v
      2. Assert: Exit code 0
      3. Assert: >= 5 tests passed
    Expected Result: Coverage metrics computation is tested
    Evidence: Test output captured
  ```

  **Commit**: YES
  - Message: `feat: compliance dashboard backend with coverage metrics computation`
  - Files: `backend/dashboard/__init__.py`, `backend/dashboard/coverage.py`, `backend/dashboard/metrics.py`, `backend/main.py`, `tests/test_dashboard.py`
  - Pre-commit: `pytest tests/test_dashboard.py -v`

### Wave 6 — Dashboard & Visualization

- [ ] 16. Visual Compliance Dashboard — Frontend (Recharts Heat Map)

  **What to do**:
  - Create new dashboard page in frontend: `/dashboard`
  - Install Recharts (already in deps? check `package.json` — if not, add it)
  - Build dashboard components:
    - **Coverage Heat Map**: Grid showing legal domains (rows) vs coverage percentage (color intensity)
      - Green: >80% coverage
      - Yellow: 50-80% coverage
      - Red: <50% coverage
      - Click cell → drill down to see specific missing articles
    - **Stats Overview Cards**: Total laws indexed, total articles, overall coverage %, last update
    - **Domain Bar Chart**: Horizontal bars showing coverage per legal domain
    - **Missing Articles List**: Expandable section showing which articles need indexing
  - Fetch data from `/api/v1/dashboard/coverage` and `/api/v1/dashboard/stats`
  - Add loading skeleton states while data loads
  - Responsive design (works on mobile and desktop)
  - Add navigation link: "Dashboard" in main app navigation
  - Write component tests for dashboard

  **Must NOT do**:
  - Do NOT add export/download functionality (defer to post-launch)
  - Do NOT add real-time updates (polling or WebSocket — static on page load is fine)
  - Do NOT add user-customizable reports or filters beyond domain
  - Do NOT change existing app navigation style — ADD new link in same style

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Data visualization with Recharts, responsive dashboard layout, color-coded heat map
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Dashboard layout design, chart component styling, responsive grid
  - **Skills Evaluated but Omitted**:
    - `typography`: Dashboard is data-heavy, not text-heavy

  **Parallelization**:
  - **Can Run In Parallel**: NO (needs Task 15 backend)
  - **Parallel Group**: Wave 6 (after Task 15)
  - **Blocks**: Tasks 17, 18 (docs and README reference dashboard)
  - **Blocked By**: Tasks 7, 15 (frontend test infra + dashboard backend)

  **References**:

  **Pattern References**:
  - `frontend/src/` — Existing page structure, layout components, Tailwind classes
  - `frontend/src/` — Design system: colors, spacing, card patterns, animation (Framer Motion)
  - `frontend/package.json` — Check if Recharts or similar charting library is already installed

  **External References**:
  - Official docs: `https://recharts.org/en-US/api` — Recharts component API
  - Official docs: `https://recharts.org/en-US/examples` — Chart examples (bar chart, heatmap patterns)
  - Example: `https://github.com/recharts/recharts` — Recharts repo for patterns

  **WHY Each Reference Matters**:
  - Existing pages: Must match the visual style (Tailwind classes, card patterns, spacing)
  - Recharts docs: Heat map isn't a native Recharts component — need to build from ScatterChart or custom cells
  - Framer Motion: Existing animations should be used for dashboard entry transitions

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify dashboard page renders with data
    Tool: Playwright (playwright skill)
    Preconditions: Frontend + backend running, coverage data available
    Steps:
      1. Navigate to: http://localhost:3000/dashboard
      2. Wait for: [data-testid="coverage-heatmap"] visible (timeout: 15s)
      3. Assert: Heat map shows colored cells
      4. Assert: Stats cards show numbers (not "Loading...")
      5. Assert: At least one domain bar chart bar is visible
      6. Screenshot: .sisyphus/evidence/task-16-dashboard.png
    Expected Result: Dashboard renders with real coverage data
    Evidence: .sisyphus/evidence/task-16-dashboard.png

  Scenario: Verify dashboard is responsive
    Tool: Playwright (playwright skill)
    Preconditions: Frontend running
    Steps:
      1. Set viewport to mobile: 375x812
      2. Navigate to: http://localhost:3000/dashboard
      3. Wait for: Dashboard content visible (timeout: 10s)
      4. Assert: No horizontal scrollbar
      5. Assert: Cards stack vertically
      6. Screenshot: .sisyphus/evidence/task-16-dashboard-mobile.png
    Expected Result: Dashboard works on mobile viewport
    Evidence: .sisyphus/evidence/task-16-dashboard-mobile.png

  Scenario: Verify heat map cell click shows detail
    Tool: Playwright (playwright skill)
    Preconditions: Dashboard loaded with data
    Steps:
      1. Navigate to: http://localhost:3000/dashboard
      2. Wait for: Heat map visible
      3. Click: First heat map cell
      4. Assert: Detail panel or tooltip shows missing articles for that domain
      5. Screenshot: .sisyphus/evidence/task-16-heatmap-detail.png
    Expected Result: Heat map is interactive with drill-down
    Evidence: .sisyphus/evidence/task-16-heatmap-detail.png
  ```

  **Commit**: YES
  - Message: `feat: visual compliance dashboard with coverage heat map`
  - Files: `frontend/src/app/dashboard/page.tsx`, `frontend/src/components/dashboard/`, `frontend/src/__tests__/dashboard.test.tsx`
  - Pre-commit: `cd frontend && npx vitest run`

---

### Wave 7 — Documentation & Presentation

- [ ] 17. VitePress Documentation Site (5+ Core Pages)

  **What to do**:
  - Initialize VitePress project in `docs/` directory
  - Configure VitePress:
    - Title: "Omnibus Legal Compass"
    - Theme customization matching project branding
    - Sidebar navigation
    - GitHub edit links
    - Search (built-in VitePress search)
  - Create core documentation pages:
    1. **Home** (`index.md`): Hero section, feature highlights, quick links
    2. **Getting Started** (`getting-started.md`): Prerequisites, installation, Docker setup, first query
    3. **Architecture** (`architecture.md`): System diagram, component overview, data flow, hybrid search explanation
    4. **API Reference** (`api-reference.md`): All endpoints with examples, request/response schemas, error codes
    5. **Knowledge Graph** (`knowledge-graph.md`): Schema explanation, how to navigate, what data is included
    6. **Features** (`features.md`): Legal Q&A, Compliance Checker, Business Guidance, Chat, Dashboard — with screenshots
    7. **Deployment** (`deployment.md`): Migrate existing DEPLOYMENT.md content, add Docker Compose guide
  - Set up GitHub Pages deployment workflow in `.github/workflows/docs.yml`
  - Add "Documentation" link to README
  - Add `docs:dev` and `docs:build` scripts to root `package.json`

  **Must NOT do**:
  - Do NOT add a blog section
  - Do NOT add i18n/translation (English only for V1)
  - Do NOT add video tutorials (screenshots and text only)
  - Do NOT duplicate README content — link to it instead

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation-heavy task requiring clear technical writing
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: VitePress has its own theming, no custom UI needed
    - `typography`: VitePress handles typography defaults well

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 7 (with Tasks 18, 19)
  - **Blocks**: Task 20 (demo screenshots reference docs)
  - **Blocked By**: Task 16 (docs reference dashboard, need screenshots)

  **References**:

  **Pattern References**:
  - `README.md` — Existing documentation to reference (not duplicate)
  - `DEPLOYMENT.md` — Content to migrate into docs site
  - `data/DATA_SCHEMA.md` — Technical reference to incorporate

  **External References**:
  - Official docs: `https://vitepress.dev/guide/getting-started` — VitePress setup
  - Official docs: `https://vitepress.dev/guide/deploy#github-pages` — GitHub Pages deployment
  - Example: `https://vitepress.dev/` — VitePress's own docs as design reference

  **WHY Each Reference Matters**:
  - `DEPLOYMENT.md`: Content should be migrated (not duplicated) into the docs site
  - VitePress deploy docs: Exact GitHub Actions workflow for Pages deployment

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify docs site builds successfully
    Tool: Bash
    Preconditions: VitePress configured in docs/
    Steps:
      1. Run: cd docs && npm run docs:build
      2. Assert: Exit code 0 (build succeeds)
      3. Run: find docs/.vitepress/dist -name "*.html" | wc -l
      4. Assert: Returns >= 7 (at least 7 HTML pages generated)
    Expected Result: Docs site builds with all pages
    Evidence: Build output + file count captured

  Scenario: Verify docs dev server renders correctly
    Tool: Playwright (playwright skill)
    Preconditions: Docs dev server running (npm run docs:dev)
    Steps:
      1. Navigate to: http://localhost:5173
      2. Wait for: Page title contains "Omnibus Legal Compass" (timeout: 10s)
      3. Assert: Sidebar navigation visible with at least 5 links
      4. Click: "Getting Started" in sidebar
      5. Assert: Page shows installation instructions
      6. Screenshot: .sisyphus/evidence/task-17-docs-site.png
    Expected Result: Docs site renders with navigation and content
    Evidence: .sisyphus/evidence/task-17-docs-site.png
  ```

  **Commit**: YES
  - Message: `docs: add VitePress documentation site with core pages`
  - Files: `docs/**`, `.github/workflows/docs.yml`, `package.json` (scripts)
  - Pre-commit: `cd docs && npm run docs:build`

---

- [ ] 18. README Full Transformation (Showcase Design)

  **What to do**:
  - Transform README.md into a Supabase/Cal.com quality showcase:
    - **Hero section**: Project name "Omnibus Legal Compass" with tagline and brief description
    - **Badges row**: CI status, License (MIT), Release version, Test coverage, Stars
    - **Architecture diagram**: Keep existing diagram, polish if needed
    - **Feature showcase**: Screenshots/GIFs for each feature (Legal Q&A, Compliance, Business, Chat, Dashboard, Knowledge Graph)
    - **"Why Omnibus Legal Compass?"** section: 3-4 bullet points highlighting unique value
    - **Quick Start**: `docker-compose up` one-command setup
    - **Competitive Comparison Table**: Link to detailed table (Task 19)
    - **Tech Stack**: Visual badges for FastAPI, Next.js, Qdrant, NVIDIA NIM, LangChain
    - **API Preview**: 2-3 curl examples showing key endpoints
    - **Contributing**: Link to CONTRIBUTING.md
    - **License**: MIT badge linking to LICENSE file
    - **Legal Disclaimer**: Prominent section
  - Use Shields.io for all badges
  - Preserve existing content that's good — enhance, don't rewrite from scratch
  - Ensure all image/GIF references use relative paths (not external URLs that may break)

  **Must NOT do**:
  - Do NOT remove existing useful content — enhance it
  - Do NOT add fake stats or badges (no made-up download counts)
  - Do NOT change the project's actual features or architecture — just document them better
  - Do NOT add emoji overload (professional, not flashy)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: README design is a visual communication task — layout, badges, screenshots placement
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Visual layout thinking for README structure
  - **Skills Evaluated but Omitted**:
    - `writing`: README is more visual than prose-heavy
    - `typography`: Markdown has limited typography control

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 7 (with Tasks 17, 19)
  - **Blocks**: Task 20 (demo GIFs go into README)
  - **Blocked By**: Task 16 (needs dashboard screenshots)

  **References**:

  **Pattern References**:
  - `README.md` (root) — Current README content to preserve and enhance
  - `DEPLOYMENT.md` — Reference for quick-start section
  - `docker-compose.yml` — For the one-command setup instructions

  **External References**:
  - Example: `https://github.com/supabase/supabase/blob/master/README.md` — Supabase README structure
  - Example: `https://github.com/calcom/cal.com/blob/main/README.md` — Cal.com README structure
  - Tool: `https://shields.io/` — Badge generation
  - Tool: `https://simpleicons.org/` — Brand icons for tech stack badges

  **WHY Each Reference Matters**:
  - Current `README.md`: Must preserve existing good content (architecture diagram, feature descriptions)
  - Supabase/Cal.com: Design references for badge layout, section ordering, visual hierarchy
  - Shields.io: Generate all badges (CI, license, coverage, etc.)

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify README has all required sections
    Tool: Bash
    Preconditions: README transformed
    Steps:
      1. Run: grep -c "## " README.md
      2. Assert: Returns >= 8 (at least 8 major sections)
      3. Run: grep -q "Quick Start" README.md && echo "OK"
      4. Assert: Output is "OK"
      5. Run: grep -q "does not constitute legal advice" README.md && echo "OK"
      6. Assert: Output is "OK" (disclaimer present)
      7. Run: grep -c "!\[" README.md
      8. Assert: Returns >= 5 (at least 5 images/badges)
    Expected Result: README has all sections, images, and disclaimer
    Evidence: Section and image counts captured

  Scenario: Verify badges are valid (not broken links)
    Tool: Bash
    Preconditions: README has badge URLs
    Steps:
      1. Run: grep -oP 'https://img\.shields\.io/[^\)]+' README.md | head -3 | while read url; do curl -s -o /dev/null -w "%{http_code}" "$url"; echo; done
      2. Assert: All return 200 (badges resolve)
    Expected Result: All Shields.io badges load correctly
    Evidence: HTTP status codes captured
  ```

  **Commit**: YES
  - Message: `docs: transform README into professional showcase with badges and visual hierarchy`
  - Files: `README.md`
  - Pre-commit: N/A

---

- [ ] 19. Competitive Comparison Table (Research & Create)

  **What to do**:
  - Create `docs/comparison.md` for VitePress docs site
  - Research and document comparison against 5 competitors:
    1. **Lawyer LLaMA** (China, 980★) — fine-tuned LLM approach
    2. **Fuzi.mingcha** (China, 365★) — academic legal AI with KG
    3. **AI Legal Compliance Assistant** (USA, 311★) — NY alcohol compliance
    4. **Explore Singapore** (Singapore, 31★) — SE Asian legal RAG
    5. **OpenNyAI** (India) — Indian legal AI ecosystem
  - Comparison axes (8 maximum):
    1. Jurisdiction coverage
    2. Frontend UI (None / Basic / Production)
    3. Hybrid Search (BM25 + Dense)
    4. Reranking (CrossEncoder)
    5. Knowledge Graph
    6. Multi-turn Chat
    7. API Documentation (OpenAPI)
    8. Active maintenance / last commit
  - Include honest assessment (don't oversell — mark competitors' strengths too)
  - Add compact version of comparison table to README (link to full version in docs)
  - Ensure all claims are verifiable (link to competitor repos)

  **Must NOT do**:
  - Do NOT make false claims about competitors
  - Do NOT include more than 5 competitors (focused comparison)
  - Do NOT include performance benchmarks (would need formal evaluation)
  - Do NOT trash competitors — professional, factual comparison only

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Research is already done (from librarian agent) — just format into table
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `writing`: Table format is structured data, not prose

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 7 (with Tasks 17, 18)
  - **Blocks**: Task 20 (README references comparison)
  - **Blocked By**: Task 16 (need all features built to compare fairly)

  **References**:

  **External References**:
  - Competitor repos: `https://github.com/AndrewZhe/lawyer-llama` — Lawyer LLaMA
  - Competitor repos: `https://github.com/irlab-sdu/fuzi.mingcha` — Fuzi.mingcha
  - Competitor repos: `https://github.com/Ramseygithub/ai-legal-compliance-assistant` — AI Legal Compliance
  - Competitor repos: `https://github.com/adityaprasad-sudo/Explore-Singapore` — Explore Singapore
  - Competitor repos: `https://github.com/OpenNyAI` — OpenNyAI organization

  **WHY Each Reference Matters**:
  - Each competitor repo must be checked for current features/status to ensure comparison is accurate and up-to-date

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify comparison table is complete
    Tool: Bash
    Preconditions: comparison.md created
    Steps:
      1. Run: grep -c "|" docs/comparison.md
      2. Assert: Returns >= 10 (table rows exist)
      3. Run: grep -c "Lawyer LLaMA\|Fuzi\|Explore Singapore\|OpenNyAI\|Legal Compliance" docs/comparison.md
      4. Assert: Returns >= 5 (all 5 competitors mentioned)
    Expected Result: Comparison table covers all competitors and axes
    Evidence: File content captured

  Scenario: Verify README has compact comparison
    Tool: Bash
    Preconditions: README updated with comparison section
    Steps:
      1. Run: grep -q "Comparison\|comparison" README.md && echo "OK"
      2. Assert: Output is "OK"
    Expected Result: README links to or embeds comparison
    Evidence: Grep output captured
  ```

  **Commit**: YES (group with Task 18)
  - Message: `docs: add competitive comparison table against 5 legal AI projects`
  - Files: `docs/comparison.md`, `README.md` (compact table)
  - Pre-commit: N/A

---

### Wave 8 — Launch Readiness

- [ ] 20. Demo Screenshots & GIFs (Capture All Features)

  **What to do**:
  - Capture high-quality screenshots of all application features:
    1. Legal Q&A — showing question, answer with citations, confidence score
    2. Multi-turn Chat — showing conversation with follow-up questions
    3. Compliance Checker — showing analysis results with recommendations
    4. Business Formation — showing step-by-step guidance
    5. Knowledge Graph — showing tree view with expanded law
    6. Dashboard — showing heat map with coverage data
    7. API docs (Swagger UI) — showing interactive documentation
  - Create GIF recordings of key user flows:
    1. "Ask a legal question → Get cited answer" (5-10 second GIF)
    2. "Navigate Knowledge Graph" (5-10 second GIF)
    3. "Check compliance" (5-10 second GIF)
  - Place all assets in `assets/` or `docs/public/images/` directory
  - Update README with screenshot references
  - Update docs site with screenshots on feature pages
  - Use consistent window size and dark/light mode for all captures

  **Must NOT do**:
  - Do NOT use fake/mock data in screenshots — use real legal document results
  - Do NOT add watermarks or branding overlays
  - Do NOT create video tutorials (just static screenshots and short GIFs)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Mechanical screenshot capture task using Playwright
  - **Skills**: [`playwright`]
    - `playwright`: Automated screenshot capture at consistent viewports
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Not designing UI, just capturing it

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 8 (with Task 21)
  - **Blocks**: Task 22 (final launch checklist needs all assets)
  - **Blocked By**: Tasks 17, 18, 19 (all pages and content must be ready)

  **References**:

  **Pattern References**:
  - `frontend/src/app/` — All pages to capture
  - `README.md` — Image reference locations
  - `docs/` — Documentation pages that need screenshots

  **WHY Each Reference Matters**:
  - Must navigate to each page to capture screenshots
  - README and docs need image paths updated to reference the captures

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify all required screenshots exist
    Tool: Bash
    Preconditions: Screenshots captured
    Steps:
      1. Run: ls assets/screenshots/ 2>/dev/null | wc -l || ls docs/public/images/ 2>/dev/null | wc -l
      2. Assert: Returns >= 7 (one per feature)
    Expected Result: All feature screenshots captured
    Evidence: File listing captured

  Scenario: Verify README references images correctly
    Tool: Bash
    Preconditions: README updated with image paths
    Steps:
      1. Run: grep -oP '!\[.*?\]\((.*?)\)' README.md | while read line; do echo "$line"; done
      2. Assert: At least 5 image references found
      3. Run: grep -oP '\((assets/[^)]+|docs/[^)]+)\)' README.md | tr -d '()' | while read path; do test -f "$path" && echo "OK: $path" || echo "MISSING: $path"; done
      4. Assert: All image paths resolve to existing files
    Expected Result: All README images link to actual files
    Evidence: Path validation output captured
  ```

  **Commit**: YES
  - Message: `docs: add feature screenshots and demo GIFs`
  - Files: `assets/screenshots/`, `README.md`, `docs/features.md`
  - Pre-commit: N/A

---

- [ ] 21. CONTRIBUTING.md & "Good First Issues" Creation

  **What to do**:
  - Create comprehensive `CONTRIBUTING.md`:
    - Welcome message and project vision
    - How to set up development environment (link to docs Getting Started)
    - Code style guide (Python: ruff/flake8 + black, TypeScript: ESLint + Prettier)
    - Branch naming convention (`feat/`, `fix/`, `docs/`, `test/`)
    - Commit message format (conventional commits: `feat:`, `fix:`, `docs:`, `test:`)
    - Pull request process (fork → branch → PR → review → merge)
    - Testing requirements (all PRs must pass CI, new features need tests)
    - How to report bugs (link to issue template)
    - How to request features (link to issue template)
    - Where to ask questions (point to issues or docs)
  - Create 10-15 GitHub Issues labeled "good first issue":
    - Examples:
      1. "Add Bahasa Indonesia translation for README" (label: good first issue, docs)
      2. "Add loading skeleton to Knowledge Graph page" (label: good first issue, frontend)
      3. "Add unit test for compliance checker endpoint" (label: good first issue, testing)
      4. "Improve error message when API key is missing" (label: good first issue, backend)
      5. "Add dark mode toggle to frontend" (label: good first issue, frontend)
      6. "Add pagination to Knowledge Graph law list" (label: good first issue, frontend)
      7. "Add type hints to ingestion scripts" (label: good first issue, backend)
      8. "Create FAQ page in documentation" (label: good first issue, docs)
      9. "Add response time metrics to API health endpoint" (label: good first issue, backend)
      10. "Add keyboard shortcuts for chat (Enter to send, Shift+Enter for newline)" (label: good first issue, frontend)
    - Each issue includes: description, files to modify, how to fix, acceptance criteria, estimated time
  - Create labels: `good first issue`, `bug`, `feature`, `docs`, `frontend`, `backend`, `testing`

  **Must NOT do**:
  - Do NOT create complex issues for "good first issue" (should be completable in 1-2 hours)
  - Do NOT add CLA (Contributor License Agreement) — overkill for V1
  - Do NOT create CODEOWNERS (too few contributors)

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation-heavy task with clear, welcoming prose
  - **Skills**: [`git-master`]
    - `git-master`: Creating GitHub issues via `gh` CLI
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: No UI work involved

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 8 (with Task 20)
  - **Blocks**: Task 22 (launch checklist verifies GFIs exist)
  - **Blocked By**: Task 3 (issue templates must exist first)

  **References**:

  **Pattern References**:
  - `.github/ISSUE_TEMPLATE/good_first_issue.md` — Template created in Task 3
  - `README.md` — Link to CONTRIBUTING.md
  - `docs/getting-started.md` — Link for dev setup instructions

  **External References**:
  - Example: `https://github.com/firstcontributions/first-contributions` — Best practice GFI patterns
  - Example: `https://github.com/supabase/supabase/blob/master/CONTRIBUTING.md` — Supabase contributing guide

  **WHY Each Reference Matters**:
  - Issue template: Use the template created in Task 3 for consistent GFI format
  - Supabase CONTRIBUTING: Reference for structure and welcoming tone

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify CONTRIBUTING.md is comprehensive
    Tool: Bash
    Preconditions: CONTRIBUTING.md created
    Steps:
      1. Run: test -f CONTRIBUTING.md && echo "EXISTS"
      2. Assert: Output is "EXISTS"
      3. Run: grep -c "## " CONTRIBUTING.md
      4. Assert: Returns >= 5 (at least 5 sections)
      5. Run: grep -qi "pull request" CONTRIBUTING.md && echo "OK"
      6. Assert: Output is "OK"
    Expected Result: Comprehensive contributing guide with all sections
    Evidence: File content captured

  Scenario: Verify Good First Issues exist
    Tool: Bash
    Preconditions: Issues created via gh CLI
    Steps:
      1. Run: gh issue list --label "good first issue" --json number,title | python -c "import json,sys; issues=json.load(sys.stdin); print(len(issues))"
      2. Assert: Returns >= 10 (at least 10 GFIs created)
    Expected Result: Good First Issues available for new contributors
    Evidence: Issue list captured
  ```

  **Commit**: YES
  - Message: `docs: add CONTRIBUTING.md and create Good First Issues`
  - Files: `CONTRIBUTING.md`
  - Pre-commit: N/A

---

- [ ] 22. Final Integration Test & Launch Checklist Verification

  **What to do**:
  - Run full integration test of the entire application:
    - Start backend + frontend + Qdrant via docker-compose
    - Verify all pages load without errors
    - Verify all API endpoints respond
    - Verify Knowledge Graph is populated
    - Verify Dashboard shows data
    - Verify Multi-turn Chat works end-to-end
    - Verify docs site builds and deploys
  - Execute launch checklist:
    - [ ] `.env` purged from git history (Task 1)
    - [ ] NVIDIA API key rotated (Task 1)
    - [ ] LICENSE file exists (Task 2)
    - [ ] CODE_OF_CONDUCT.md exists (Task 2)
    - [ ] SECURITY.md exists (Task 2)
    - [ ] Legal disclaimer in footer (Task 2)
    - [ ] GitHub templates exist (Task 3)
    - [ ] CI/CD pipeline passes (Task 4)
    - [ ] Zero LSP errors (Task 5)
    - [ ] >80% backend test coverage (Task 6)
    - [ ] Frontend tests pass (Task 7)
    - [ ] Rate limiting works (Task 8)
    - [ ] OpenAPI spec valid (Task 9)
    - [ ] Knowledge Graph loads (Tasks 10-12)
    - [ ] Multi-turn Chat works (Tasks 13-14)
    - [ ] Dashboard renders (Tasks 15-16)
    - [ ] Docs site builds (Task 17)
    - [ ] README has badges + screenshots (Task 18)
    - [ ] Comparison table complete (Task 19)
    - [ ] Screenshots captured (Task 20)
    - [ ] CONTRIBUTING.md exists (Task 21)
    - [ ] Good First Issues created (Task 21)
  - Fix any integration issues discovered
  - Run final full test suite: `pytest tests/ --cov=backend --cov-fail-under=80`
  - Verify docker-compose setup works from scratch (clean state)

  **Must NOT do**:
  - Do NOT deploy to production — this is local verification only
  - Do NOT push to public repository (user decides when to go public)
  - Do NOT create GitHub releases or tags (user decides versioning)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Full system integration verification requires thorough testing across all components
  - **Skills**: [`playwright`, `git-master`]
    - `playwright`: Browser-based verification of all UI features
    - `git-master`: Final commit and git status verification
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: No design work, only verification

  **Parallelization**:
  - **Can Run In Parallel**: NO (final sequential task)
  - **Parallel Group**: Wave 8 (solo — FINAL)
  - **Blocks**: None (last task)
  - **Blocked By**: Tasks 20, 21 (everything must be done)

  **References**:

  **Pattern References**:
  - `docker-compose.yml` — Docker setup to verify
  - `README.md` — Quick start instructions to validate
  - All task acceptance criteria from Tasks 1-21

  **WHY Each Reference Matters**:
  - `docker-compose.yml`: Final test starts everything from scratch using Docker
  - All previous acceptance criteria: This task verifies the ENTIRE plan succeeded

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify full application starts from docker-compose
    Tool: Bash
    Preconditions: Docker installed, clean state
    Steps:
      1. Run: docker-compose down -v 2>/dev/null; docker-compose up -d
      2. Wait: 30 seconds for services to start
      3. Run: curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health
      4. Assert: Returns 200 (backend healthy)
      5. Run: curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
      6. Assert: Returns 200 (frontend healthy)
    Expected Result: Full application starts and responds
    Evidence: HTTP status codes captured

  Scenario: Verify all features are accessible end-to-end
    Tool: Playwright (playwright skill)
    Preconditions: Application running via docker-compose
    Steps:
      1. Navigate to: http://localhost:3000
      2. Assert: Home page loads
      3. Navigate to: http://localhost:3000/knowledge-graph
      4. Assert: Knowledge Graph page loads with data
      5. Navigate to: http://localhost:3000/dashboard
      6. Assert: Dashboard page loads with heat map
      7. Screenshot: .sisyphus/evidence/task-22-full-integration.png
    Expected Result: All pages load and display data
    Evidence: .sisyphus/evidence/task-22-full-integration.png

  Scenario: Verify full test suite passes
    Tool: Bash
    Preconditions: All code complete
    Steps:
      1. Run: pytest tests/ --cov=backend --cov-fail-under=80 -v
      2. Assert: Exit code 0 (all tests pass, coverage met)
      3. Run: cd frontend && npx vitest run
      4. Assert: Exit code 0 (all frontend tests pass)
    Expected Result: 100% test pass rate, >80% coverage
    Evidence: Full test output captured

  Scenario: Verify launch checklist items
    Tool: Bash
    Preconditions: All 21 tasks completed
    Steps:
      1. Run: git log --all -S "NVIDIA_API_KEY" --oneline | wc -l
      2. Assert: Returns 0 (secrets purged)
      3. Run: test -f LICENSE && test -f CONTRIBUTING.md && test -f CODE_OF_CONDUCT.md && test -f SECURITY.md && echo "ALL_EXIST"
      4. Assert: Output is "ALL_EXIST"
      5. Run: gh issue list --label "good first issue" --json number | python -c "import json,sys; print(len(json.load(sys.stdin)))"
      6. Assert: Returns >= 10
    Expected Result: All checklist items verified
    Evidence: Checklist verification output captured
  ```

  **Commit**: YES
  - Message: `chore: verify full integration and launch readiness`
  - Files: Any integration fixes needed
  - Pre-commit: `pytest tests/ --cov=backend --cov-fail-under=80`

---

## Commit Strategy

| After Task | Message | Key Files | Verification |
|-----------|---------|-----------|-------------|
| 1 | `security: purge .env from git history and add secret detection` | `.gitignore`, `.env.example`, `.pre-commit-config.yaml` | `git log --all -S "NVIDIA_API_KEY"` returns 0 |
| 2 | `docs: add LICENSE, CODE_OF_CONDUCT, SECURITY.md, and legal disclaimers` | `LICENSE`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, frontend footer | `test -f LICENSE` |
| 3 | `chore: add GitHub issue and PR templates` | `.github/ISSUE_TEMPLATE/*.md`, `.github/PULL_REQUEST_TEMPLATE.md` | Template files exist |
| 4 | `ci: add GitHub Actions CI/CD pipeline and test infrastructure` | `.github/workflows/ci.yml`, `pytest.ini`, `vitest.config.ts`, `conftest.py` | `pytest tests/ -v` passes |
| 5 | `fix: resolve all type errors in backend (main.py, retriever.py)` | `backend/main.py`, `backend/retriever.py` | Zero pyright errors |
| 6 | `test: add comprehensive backend test suite (>80% coverage)` | `tests/test_rag_chain.py`, `tests/test_api.py`, `tests/test_scripts.py` | `pytest --cov-fail-under=80` |
| 7 | `test: add frontend component tests with Vitest + RTL` | `frontend/src/__tests__/*.test.tsx` | `npx vitest run` passes |
| 8 | `feat: add API rate limiting with slowapi` | `backend/main.py`, `backend/requirements.txt` | 429 after threshold |
| 9 | `feat: API v1 versioning with enhanced OpenAPI documentation` | `backend/main.py`, `backend/models/` | OpenAPI spec valid |
| 10 | `feat: knowledge graph schema design with Pydantic + NetworkX` | `backend/knowledge_graph/` | Schema models importable |
| 11 | `feat: knowledge graph data ingestion from legal documents` | `backend/knowledge_graph/ingest.py`, `data/knowledge_graph.json` | Graph populated |
| 12 | `feat: knowledge graph API endpoints and frontend navigation UI` | `backend/main.py`, `frontend/src/app/knowledge-graph/` | API returns data, UI renders |
| 13 | `feat: multi-turn chat with session management and context window` | `backend/chat/` | Follow-up queries use context |
| 14 | `feat: multi-turn chat UI with conversation history` | `frontend/src/components/chat/` | Chat bubbles render |
| 15 | `feat: compliance dashboard backend with coverage metrics` | `backend/dashboard/` | Coverage API returns data |
| 16 | `feat: visual compliance dashboard with coverage heat map` | `frontend/src/app/dashboard/` | Heat map renders |
| 17 | `docs: add VitePress documentation site with core pages` | `docs/**` | `docs:build` succeeds |
| 18 | `docs: transform README into professional showcase` | `README.md` | >= 8 sections, >= 5 images |
| 19 | `docs: add competitive comparison table` | `docs/comparison.md`, `README.md` | 5 competitors, 8 axes |
| 20 | `docs: add feature screenshots and demo GIFs` | `assets/screenshots/` | >= 7 screenshots |
| 21 | `docs: add CONTRIBUTING.md and create Good First Issues` | `CONTRIBUTING.md` | >= 10 GFIs on GitHub |
| 22 | `chore: verify full integration and launch readiness` | Any fixes needed | Full test suite passes |

---

## Success Criteria

### Verification Commands
```bash
# Security: No secrets in git history
git log --all -S "NVIDIA_API_KEY" --oneline  # Expected: empty output

# Tests: Full suite passes with coverage
pytest tests/ --cov=backend --cov-fail-under=80 -v  # Expected: exit 0
cd frontend && npx vitest run  # Expected: exit 0

# Type safety: No backend type errors
pyright backend/main.py backend/retriever.py  # Expected: 0 errors

# API: OpenAPI spec is valid
curl -s http://localhost:8000/openapi.json | python -m json.tool > /dev/null  # Expected: exit 0

# Docs: VitePress builds
cd docs && npm run docs:build  # Expected: exit 0

# OSS files: All required files exist
test -f LICENSE && test -f CONTRIBUTING.md && test -f CODE_OF_CONDUCT.md && test -f SECURITY.md && echo "ALL EXIST"

# CI: GitHub Actions workflow exists
test -f .github/workflows/ci.yml && echo "CI EXISTS"

# Good First Issues: At least 10
gh issue list --label "good first issue" --json number | python -c "import json,sys; print(len(json.load(sys.stdin)))"  # Expected: >= 10
```

### Final Checklist
- [ ] All "Must Have" present (LICENSE, CI, disclaimers, >80% coverage, diagram, comparison)
- [ ] All "Must NOT Have" absent (no auth, no mobile, no blockchain, no i18n, no broken existing UI)
- [ ] All 22 tasks completed with acceptance criteria verified
- [ ] Full test suite passes (backend + frontend)
- [ ] Docker-compose starts cleanly from scratch
- [ ] README has showcase quality (badges, screenshots, quick-start, comparison)
- [ ] Documentation site builds and has 7+ pages
- [ ] Knowledge Graph populated and navigable
- [ ] Multi-turn Chat works with follow-up questions
- [ ] Dashboard shows coverage heat map
- [ ] API has versioned endpoints with OpenAPI spec
- [ ] 10+ Good First Issues created on GitHub
- [ ] No secrets in git history
