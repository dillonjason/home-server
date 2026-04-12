# Home Server Configuration

Docker Compose configuration for a self-hosted home server running at `dillonjason.dev`.

## Services

### Media
| Service | Description | Port |
|---|---|---|
| [Jellyfin](https://jellyfin.org) | Media server for movies and TV | 8096 |
| [Sonarr](https://sonarr.tv) | TV show collection manager | — |
| [Radarr](https://radarr.video) | Movie collection manager | — |
| [Bazarr](https://www.bazarr.media) | Subtitle manager for Sonarr/Radarr | 6767 |
| [Transmission](https://transmissionbt.com) | Torrent client (routed through OpenVPN) | 9091 |
| [Jackett](https://github.com/Jackett/Jackett) | Torrent indexer proxy | — |

### Home Automation
| Service | Description |
|---|---|
| [Home Assistant](https://www.home-assistant.io) | Home automation hub (Zigbee via USB stick) |
| [Homebridge](https://homebridge.io) | Bridges non-HomeKit devices to Apple HomeKit |
| [AirConnect](https://github.com/philippe44/AirConnect) | AirPlay bridge for non-AirPlay devices |

### Infrastructure & Monitoring
| Service | Description | Port |
|---|---|---|
| [SWAG](https://docs.linuxserver.io/general/swag) | Nginx reverse proxy with SSL (Cloudflare DNS) | 443 |
| [Authelia](https://www.authelia.com) | SSO and 2FA authentication portal | — |
| [Homer](https://github.com/bastienwirtz/homer) | Service dashboard | 8080 |
| [Portainer](https://www.portainer.io) | Docker container management UI | — |
| [Grafana](https://grafana.com) | Metrics dashboards | — |
| [Prometheus](https://prometheus.io) | Metrics collection | — |
| node_exporter | Host system metrics for Prometheus | — |
| cAdvisor | Container metrics for Prometheus | — |
| [Redis](https://redis.io) | In-memory data store (used by Authelia) | — |

### Development
| Service | Description | Port |
|---|---|---|
| [code-server](https://github.com/coder/code-server) | VS Code in the browser | — |
| [virt-manager](https://virt-manager.org) | KVM virtual machine manager | 8185 |

### Other
| Service | Description |
|---|---|
| [Valheim](https://github.com/lloesche/valheim-server) | Dedicated Valheim game server |
| [Actual Budget](https://actualbudget.org) | Local-first personal finance app |

## Network

All services are exposed through SWAG at `dillonjason.dev` using Cloudflare DNS validation for SSL. Authelia provides SSO and 2FA in front of protected services.

```
Internet → SWAG (443) → Authelia → Service
```

## Directory Structure

Each service has its own directory for config volumes. Secrets (API keys, passwords, certs) are gitignored — see [`.gitignore`](.gitignore).

```
home-server/
├── docker-compose.yml
├── swag/           # Nginx reverse proxy config
├── authelia/       # SSO config (secrets gitignored)
├── homer/          # Dashboard config
├── jellyfin/       # Media server config
├── sonarr/         # TV manager config
├── radarr/         # Movie manager config
├── bazarr/         # Subtitle manager config
├── transmission/   # Torrent client config (.env gitignored)
├── jackett/        # Indexer config
├── homeassistant/  # HA config (secrets/storage gitignored)
├── homebridge/     # Homebridge config
├── grafana/        # Grafana config and dashboards
├── prometheus/     # Prometheus scrape config
├── redis/          # Redis data
├── actual-data/    # Actual Budget data (gitignored)
├── code-server/    # code-server config (.ssh gitignored)
├── valheim-server/ # Valheim server config
└── win10.xml       # libvirt VM definition
```

## Getting Started

1. Clone the repo
2. Create required secret files:
   ```
   authelia/secrets/jwt
   authelia/secrets/encryption_key
   authelia/secrets/smtp
   authelia/secrets/session
   transmission/.env
   ```
3. Configure `swag/config/nginx` with your domain
4. Configure `authelia/config/configuration.yml`
5. Start services:
   ```bash
   docker compose up -d
   ```
