---
name: Execution Process
description: How to approach work in this environment — commits, tests, and safety
type: feedback
originSessionId: 17626060-a76f-4db4-8bf2-f799a151a4c6
---
Make small, focused commits and push them to GitHub after changes to any repo accessible from the container (home-server and any others granted access).

**Why:** Changes should be persisted and version-controlled continuously, not batched. The container can be rebuilt at any time.

**How to apply:** After completing a logical unit of work in any repo, stage relevant files, commit with a descriptive message, and push. Don't wait until the end of a session.

---

Suggest and create test files wherever reasonable.

**Why:** User wants test coverage as a default habit, not an afterthought.

**How to apply:** When adding or modifying logic, proactively propose test files. Write them unless the user declines.

---

Be cautious about security — treat all work as potentially web-exposed.

**Why:** Many services managed in this container (via home-server docker-compose) are exposed to the open internet (behind SWAG/reverse proxy). A mistake here can be a public vulnerability.

**How to apply:** Default to least-privilege configs, never commit secrets or credentials, validate inputs at service boundaries, flag any change that touches network-exposed services, and follow OWASP top-10 hygiene. When in doubt, ask before exposing a new surface.
