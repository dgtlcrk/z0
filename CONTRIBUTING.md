# Contributing to z0

Thank you for considering a contribution to z0.

z0 is an early-stage IRC network automation and diagnostics platform. Small,
focused improvements with tests and documentation are preferred.

## Development requirements

- Python 3.12 or newer
- Docker
- Git
- Linux or a Linux-compatible development environment

The Docker image also uses:

- `ping`
- `traceroute`
- `whois`

## Development setup

Clone the repository:

```bash
git clone https://github.com/dgtlcrk/z0.git
cd z0
```

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the project and development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e . -r requirements-dev.txt
```

Create local configuration:

```bash
cp .env.example .env
```

Do not commit `.env` or any production credentials.

## Create a branch

Use a focused branch name:

```bash
git switch -c feature/example-change
```

Common branch prefixes include:

- `feature/`
- `fix/`
- `docs/`
- `test/`
- `chore/`

## Run the validation suite

Before opening a pull request, run:

```bash
python -m compileall -q z0
python -m ruff check .
python -m pytest
docker build -t z0:test .
```

All checks should pass.

## Tests

Changes to application behavior should include tests.

Current test areas include:

- Environment configuration
- Bot identity behavior
- Core command output
- Uptime formatting
- Network-target validation
- Rejection of unsafe command input

Tests belong in the `tests/` directory.

## Pull requests

Pull requests should:

- Explain the problem being solved
- Describe the proposed solution
- Keep unrelated changes separate
- Include tests for new behavior
- Update documentation when commands or configuration change
- Pass linting, tests, compilation, and Docker build checks

## Commit messages

Use short, imperative commit messages.

Examples:

```text
Add IRC TLS configuration
Fix traceroute timeout handling
Document Docker deployment
Test invalid network targets
```

## Security and secrets

Never commit:

- `.env` files
- API keys or access tokens
- Passwords
- Private keys
- Terraform state
- Live `terraform.tfvars`
- Terraform plans
- Cloud credentials
- Private deployment identifiers that are not intended for publication

Report suspected vulnerabilities according to `SECURITY.md`.

## Network safety

z0 can generate real DNS, WHOIS, ICMP, and traceroute traffic.

Only test against systems and networks where you have authorization.
