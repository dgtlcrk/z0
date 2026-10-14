# z0_n3t

z0_n3t is a Python-based network automation and operations platform running on
Linux, Docker, and Raspberry Pi.

The platform provides a unified command-line interface, system inventory,
infrastructure health checks, scheduled plugin execution, Docker operations,
an HTTP API, and IRC/BotOps integration.

## Current Capabilities

- Human-readable platform status dashboard
- JSON output for automation
- Raspberry Pi and Linux system inventory
- Service and infrastructure health monitoring
- Plugin discovery and execution
- Persistent scheduler jobs
- Docker engine and container operations
- HTTP JSON API
- IRC/BotOps runtime
- Linux-native network edge status
- AT&T BGW320 gateway health and WAN monitoring
- Linux neighbor-table visibility
- Active IPv4 LAN discovery
- Normalized LAN device inventory
- Persistent network device inventory
- Device first-seen and last-seen tracking
- ONLINE, STALE, and OFFLINE device lifecycle state
- Prometheus, Grafana, and Jenkins integration
- Installable Python console commands
- Automated tests and input validation

## Runtime Architecture

```text
Raspberry Pi host
|
|-- z0-api.service
|   `-- z0-platform api
|       `-- HTTP API on 127.0.0.1:8081
|
|-- z0-scheduler.service
|   `-- z0-platform jobs daemon --poll 5
|       `-- Executes scheduled plugin jobs
|
`-- Docker
    |-- z0         IRC/BotOps runtime
    |-- prometheus Metrics collection
    |-- grafana    Monitoring dashboards
    `-- jenkins    Automation server
```

## Requirements

- Python 3.12 or newer
- Linux
- Git
- Docker
- Python virtual environment support

The current primary deployment runs on Ubuntu 24.04 LTS on a Raspberry Pi 4.

## Installation

Clone the repository:

```bash
git clone https://github.com/dgtlcrk/z0.git
cd z0
```

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project and development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e . -r requirements-dev.txt
```

Verify the installation:

```bash
z0 version
z0 --help
```

## Command-Line Interface

### Platform status

```bash
z0 status
```

Machine-readable output:

```bash
z0 status --json
```

### Adapters

```bash
z0 adapters
z0 adapters --json
```

### Plugins

```bash
z0 plugins
z0 plugins --json
```

### Scheduler

```bash
z0 jobs list
z0 jobs list --json
```

### Network Edge Status

Show local network edge information:

```bash
z0 network status
z0 network status --json
```

The command reports the active interface, local IPv4 address, connected
network, default gateway, gateway reachability, DNS server, DNS health,
IPv4 Internet connectivity, and IPv6 availability.

### Internet Gateway

Show the local Internet gateway and WAN status:

```bash
z0 network gateway
z0 network gateway --json
```

The current AT&T BGW320 integration reports gateway identity, software and
hardware versions, WAN source and connection state, public IPv4 address,
upstream gateway, DNS servers, MTU, packet drops and errors, PON status,
and UNI status.

### BGW320 LAN Device Records

Read the BGW320 device page without changing persistent inventory:

```bash
z0 network gateway-devices
z0 network gateway-devices --json
```

For repeatable offline testing against a saved page:

```bash
z0 network gateway-devices --html-file /tmp/z0-bgw-devices.html
```

This collector preserves the gateway's on/off state and last-activity value as
reported. It does **not** modify inventory or equate gateway state with ping
reachability. The existing gateway fetch disables TLS certificate validation
for the local self-signed BGW320 and should be hardened before expansion.

### Unified LAN Observations (read-only)

Combine BGW320 historical and current device records with local ARP and ICMP
observations without modifying persistent inventory:

```bash
z0 network unified
z0 network unified --json
```

Device identity is keyed by MAC where available. Gateway `on/off` status is
kept separate from observed reachability. `GATEWAY_ON` is not an ICMP
confirmation, and devices missing from local discovery are not automatically
marked offline. This initial command does not write to
`~/.config/z0/network_inventory.json`.

### Network Neighbors

Show the Linux kernel neighbor table:

```bash
z0 network neighbors
z0 network neighbors --json
```

This is the raw operational view and can include LAN, IPv6, and Docker
neighbor entries.

### LAN Discovery

Actively discover reachable hosts on the directly connected IPv4 network:

```bash
z0 network discover
z0 network discover --json
```

Discovery uses concurrent ICMP probing and correlates reachable hosts with
Linux neighbor data and hostname information.

### LAN Devices

Show the normalized LAN device view:

```bash
z0 network devices
z0 network devices --json
```

The device view combines local host information, active discovery, Linux
neighbor observations, and gateway identity into normalized records.

### Persistent Network Inventory

Refresh persistent network inventory:

```bash
z0 inventory update
```

List known devices:

```bash
z0 inventory list
z0 inventory list --json
```

Inventory is stored under:

```text
~/.config/z0/network_inventory.json
```

Persistent inventory retains device identity and state across discovery runs,
including IP address, MAC address, hostname, role, source, first-seen time,
last-seen time, and lifecycle state.

### Version

```bash
z0 version
z0 --version
```

## Docker Operations

Show Docker engine status:

```bash
z0 docker status
```

List running containers:

```bash
z0 docker ps
```

Include stopped containers:

```bash
z0 docker ps --all
```

Show Docker engine information:

```bash
z0 docker info
```

Show container resource usage:

```bash
z0 docker stats
z0 docker stats jenkins
```

Inspect a container:

```bash
z0 docker inspect CONTAINER
```

View container logs:

```bash
z0 docker logs CONTAINER
z0 docker logs CONTAINER --tail 50
```

Restart a container:

```bash
z0 docker restart CONTAINER
```

## HTTP API

The API listens locally on:

```text
http://127.0.0.1:8081
```

Check the API:

```bash
curl -s http://127.0.0.1:8081/ | python -m json.tool
```

Available endpoints include:

```text
/api/status
/api/system
/api/inventory
/api/services
/api/health
/api/adapters
/api/plugins
/api/jobs
/api/project
/api/docker
/api/docker/info
/api/docker/inspect
/api/docker/stats
/api/docker/logs
```

## Systemd Services

The API runs under:

```text
z0-api.service
```

The scheduler runs under:

```text
z0-scheduler.service
```

Check both services:

```bash
sudo systemctl status z0-api --no-pager
sudo systemctl status z0-scheduler --no-pager
```

Restart them:

```bash
sudo systemctl restart z0-api z0-scheduler
```

View logs:

```bash
sudo journalctl -u z0-api -n 100 --no-pager
sudo journalctl -u z0-scheduler -n 100 --no-pager
```

Systemd unit files are stored in:

```text
deploy/systemd/
```

## Configuration

Platform defaults are stored in:

```text
z0/config/default.toml
```

BotOps host configuration is loaded from:

```text
~/.config/z0/botops.env
```

The Docker IRC/BotOps runtime uses environment variables from the local
`.env` file.

Never commit credentials, passwords, private keys, Terraform state, or live
environment files.

## Development

Activate the virtual environment:

```bash
cd ~/projects/z0
source .venv/bin/activate
```

Run the test suite:

```bash
python -m pytest
```

Run Ruff against files being changed:

```bash
python -m ruff check PATHS...
```

Check for whitespace errors:

```bash
git diff --check
```

Install the current source into the virtual environment:

```bash
pip install --force-reinstall --no-deps .
hash -r
```

Restart long-running services after installation:

```bash
sudo systemctl restart z0-api z0-scheduler
```

## Repository Layout

```text
z0/
|-- deploy/
|   `-- systemd/
|       |-- z0-api.service
|       `-- z0-scheduler.service
|-- docs/
|-- tests/
|-- z0/
|   |-- adapters/
|   |-- api/
|   |-- botops/
|   |-- config/
|   |-- core/
|   |-- dockerops/
|   |-- plugins/
|   |-- scheduler/
|   |-- network/
|   |   |-- devices.py
|   |   |-- discovery.py
|   |   |-- gateway.py
|   |   |-- inventory.py
|   |   |-- neighbors.py
|   |   `-- status.py
|   |-- docker_cli.py
|   |-- platform_cli.py
|   `-- unified_cli.py
|-- Dockerfile
|-- pyproject.toml
|-- README.md
`-- CHANGELOG.md
```

## Security

Network diagnostics and future discovery features must only be used against
systems and networks where authorization has been granted.

The API currently binds to `127.0.0.1`. Do not expose it publicly without
authentication, authorization, TLS, and appropriate network controls.

Do not expose Docker restart, logs, inspection, or future device-configuration
operations to untrusted users.

## Roadmap

Network edge discovery and persistent device inventory were delivered in
z0_n3t v1.2.0.

The next development phase focuses on turning discovered network endpoints
into identifiable and manageable infrastructure.

Planned capabilities include:

```text
z0 inventory show DEVICE
z0 inventory new
z0 inventory offline
z0 device status DEVICE
```

Later phases will add:

- Device classification and managed-device onboarding
- SSH device execution
- Cisco switch and router automation
- Firewall integration
- Configuration collection and backup
- Palo Alto integration
- F5 integration
- AWS nodes
- Multi-node management
- Web dashboard

## Documentation

Release history is maintained in:

```text
CHANGELOG.md
```

## Author

Created and maintained by **Lorenzo Brown**
GitHub: **dgtlcrk**

## License

Licensed under the Apache License, Version 2.0.

See `LICENSE` for the complete license terms.

### Opt-in version-2 unified inventory

The new persistent unified inventory is independent of the existing
`~/.config/z0/network_inventory.json` file and does not modify it.

```bash
z0 inventory unified-list
z0 inventory unified-update
z0 inventory unified-list --json
```

The first `unified-update` creates
`~/.config/z0/unified_inventory_v2.json` using atomic file replacement.
Records retain first observed, last observed, last independently confirmed
online (ICMP/local), observation counts, and the latest source list. Devices
missing from a later scan become `NOT_OBSERVED`, **not OFFLINE**. The BGW320
`on` indication is not independently confirmed reachability. If the stored
JSON is corrupt or has an unfamiliar schema, updates abort instead of wiping
records. The command is manual/opt-in and does not install a scheduled task.


### Read-only network state intelligence

```bash
z0 inventory assess
z0 inventory assess --stale-hours 48
z0 inventory assess --json
```

This command reads the v2 persistent inventory **without scanning or writing**.
Previously independently reachable devices that were absent from the last scan
for longer than the threshold are flagged `SUSPECT`, **not** `OFFLINE`.
The BGW320-only `on` state is reported as `GATEWAY_REPORTED`. Devices
without a confirmed reachability history never become suspect solely because
they are old gateway records. Offline confirmation requires negative-probe
history not yet stored by schema v2. No notifications or schedules are created.

### Manual availability monitoring (opt-in)

Each invocation runs **one** ICMP check per explicitly selected private IPv4 target:

```bash
z0 network availability --ip 192.168.1.254
z0 network availability --ip 192.168.1.254 --ip 192.168.1.229
z0 network availability --ip 192.168.1.254 --failures 3 --recovery 2
z0 network availability-list --json
```

The first failed check does not establish an outage. After three consecutive
failed manual checks a target is `UNAVAILABLE`. Two consecutive successful
checks restore `AVAILABLE`; until a threshold is met a new target is
`UNCONFIRMED`. Failed probes are ICMP failures only: devices that do not
respond to ping can be listed unavailable despite still being powered on.

Results are persisted in a separate versioned file,
`~/.config/z0/availability_v1.json`. The unified and legacy network
inventories are unaffected. No scheduler, alerts, or background jobs are
installed. Only explicitly supplied private IPv4 addresses are probed;
maximum 16 per call. Avoid monitoring sleeping mobile devices.

### Offline availability simulation and transition history

```bash
z0 network availability-simulate --ip 192.168.1.254 --sequence FFFSS
z0 network availability-sim-history
z0 network availability-sim-history --json
```

`S` simulates a successful ICMP check and `F` a failed check. Each
command replays the exact sequence **without sending packets**. Consecutive
failures (default 3) transition to `UNAVAILABLE`, and consecutive successes
(default 2) recover to `AVAILABLE`. State-change events are appended to a
separate `~/.config/z0/availability_simulation_v1.json` file; repeated
invocations resume the simulated state. The real availability history and
unified inventory are not modified. No scheduler or alerts are added.

### Real manual availability event history

```bash
z0 network availability --ip 192.168.1.254
z0 network availability-events
z0 network availability-events --json
```

Manual probes now append a timestamped event **only when the confirmed
availability state changes** (for example, UNCONFIRMED to UNAVAILABLE or
UNAVAILABLE to AVAILABLE). Events are saved atomically with the host states
in the same `availability_v1.json` file. Older v1 files without events
remain readable. No scheduler, alerts, or automatic probing are introduced.

### Read-only CLI monitoring dashboard

```bash
z0 network dashboard
z0 network dashboard --events 5
z0 network dashboard --json
```

Summarizes the latest **saved** unified inventory v2, manual availability
state, and real transition events. This command only reads existing JSON
snapshots. It does not refresh the network, ping hosts, write inventory,
start background monitoring, or send notifications. The displayed data may
be stale until the corresponding manual collection commands are run.

### Local web monitoring dashboard (read-only)

The existing z0 API now serves a browser UI and saved-data endpoints:

- `/monitor` — browser dashboard
- `/api/network/dashboard` — saved inventory counts, availability and events
- `/api/network/devices` — saved unified inventory records

No extra process or frontend dependency is required. The dashboard refresh
button **re-reads local snapshot files only**. It does not ping devices or
modify monitoring or inventory records.

For secure local access, run/bind the API to loopback and use an SSH tunnel:

```bash
ssh -L 8081:127.0.0.1:8081 zo@192.168.1.229
```

Then browse to `http://127.0.0.1:8081/monitor` on your own computer.
If an API service already runs on port 8081, reuse that service after
installing the new code; do not launch a second instance on the same port.
Avoid exposing these local device details on an unauthenticated public
interface. The existing API configuration determines its bind address.

### Web inventory search, filters and friendly labels

The browser monitoring page at `/monitor` supports client-side searching by
IP, name, state and MAC; state filters; IP/name/state/MAC sorting; and compact
state indicators. Refresh reloads saved data only.

Optionally create `~/.config/z0/device_labels.json` with a mapping from
real MAC addresses to your own device names:

```json
{
  "ea:5b:ca:3d:17:c2": "My MacBook Air"
}
```

This separate file is **read-only to z0**. It never changes the unified
inventory database. Labels appear as `display_name` in
`/api/network/devices`; the original `hostname` remains unchanged. Leave
the file absent to use observed names. Keep it private because it identifies
your personal network devices.

### Saved device details (read-only)

In `/monitor`, click or keyboard-select a device row (Enter or Space)
to open the device detail panel. It shows the saved observed name, any
optional friendly label, IP, MAC, inventory state, source names, first and
last observations, observation count, and the most recent confirmed
online timestamp. If a matching IP has manual availability records, the
panel shows its saved availability and all recorded real transitions.

The `GET /api/network/device?mac=48:e2:ad:86:ff:61` endpoint returns
the same detail data as JSON. It accepts an exact MAC or saved IP address
under the `mac` parameter. Missing devices return 404. No scanning, probing,
inventory edits, or activity scheduling occurs.

### Browser device presentation

The device detail panel displays saved first/last observation and monitoring
timestamps in the **browser's local time zone** with its time-zone abbreviation.
Missing values read *Not reported* (or *Not recorded* for absent timestamps).
Discovery and verified manual availability have separate headings so a gateway
report is not mistaken for an ICMP reachability check. These are presentation
changes only: JSON data, stored snapshots and network operations are unchanged.

### Optional API password protection (PR #49)

The z0 API supports opt-in HTTP Basic authentication across **all routes**,
including `/monitor`, `/api/network/*`, `/api/docker/*`, and `/`.
This is for a single trusted operator, **not** a multiuser login system.

Set both `Z0_API_AUTH_USERNAME` and `Z0_API_AUTH_PASSWORD` in the API
service's environment. When both are absent, compatibility mode remains
unauthenticated; if only one is set, requests fail closed with HTTP 503.
Unrecognized credentials receive HTTP 401 with a browser login prompt.
Passwords must never be committed to Git or placed in the Caddyfile.

On a Pi with the z0 API behind Caddy, keep the application bound to
`127.0.0.1:8081`, and continue to use your trusted
`https://192.168.1.229/monitor` HTTPS address. HTTP Basic credentials are
transmitted as an encoded (not encrypted) header, so **never expose this
mechanism over plain HTTP on the LAN**.

For a systemd deployment, use a root-owned 0600 environment file such as
`/etc/z0-api-auth.env` containing:

```ini
Z0_API_AUTH_USERNAME=admin
Z0_API_AUTH_PASSWORD=REPLACE_WITH_UNIQUE_LONG_SECRET
```

Add `EnvironmentFile=/etc/z0-api-auth.env` in a dedicated
`systemctl edit z0-api.service` override under `[Service]`, then reload
systemd and restart **only** `z0-api.service`. Use a local terminal editor
rather than entering a password into shell history. The systemd manager
reads the protected environment file; anyone who can read the process
environment or has administrative access to the Pi should be trusted.
Browser Basic authentication remembers credentials until the browser
session expires; it is not a logout-oriented session system.

Before enabling on the live Pi, test the PR against its isolated HTTP
server tests; verify Caddy proxying and that the new browser login
challenge works after deployment. No changes to the Caddyfile, Docker
containers, IRC bot, or inventory files are required.
