---
name: User Environment
description: The runtime environment Claude Code operates in — docker container running code-server
type: user
originSessionId: 17626060-a76f-4db4-8bf2-f799a151a4c6
---
Claude Code runs inside a Docker container for code-server. The container is defined in and managed by the docker-compose file at `/home/coder/home-server/docker-compose.yml`.

**How to apply:** When suggesting system-level changes, file paths outside the container, or host-level operations, keep in mind this is a containerized environment. Configuration for the code-server container lives in `/home/coder/home-server/`.
