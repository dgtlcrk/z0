from __future__ import annotations

import ipaddress
import re
import shutil
import socket
import subprocess

VALID_HOSTNAME = re.compile(
    r"^(?=.{1,253}$)(?!-)"
    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
)


def _valid_target(target: str) -> bool:
    """Allow only normal IP addresses and DNS hostnames."""
    target = target.strip().rstrip(".")

    if not target:
        return False

    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return bool(VALID_HOSTNAME.fullmatch(target))


def dns(host: str) -> str:
    """Resolve all IPv4 and IPv6 addresses for a hostname."""
    host = host.strip().rstrip(".")

    if not _valid_target(host):
        return "Usage: !dns <hostname>"

    try:
        records = socket.getaddrinfo(host, None)
        addresses = sorted({record[4][0] for record in records})

        if not addresses:
            return f"No addresses found for {host}"

        return f"DNS {host}: {', '.join(addresses[:8])}"
    except socket.gaierror as error:
        return f"DNS lookup failed for {host}: {error}"


def whois(domain: str) -> str:
    """Return a compact WHOIS summary."""
    domain = domain.strip().lower().rstrip(".")

    if not _valid_target(domain):
        return "Usage: !whois <domain>"

    executable = shutil.which("whois")
    if executable is None:
        return "WHOIS is unavailable inside the container"

    try:
        result = subprocess.run(
            [executable, domain],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"WHOIS lookup timed out for {domain}"
    except OSError as error:
        return f"WHOIS lookup failed: {error}"

    output = result.stdout or result.stderr
    fields = {
        "registrar": None,
        "creation date": None,
        "registry expiry date": None,
        "expiration date": None,
    }

    for line in output.splitlines():
        normalized = line.strip()
        lowered = normalized.lower()

        for field in fields:
            prefix = f"{field}:"
            if lowered.startswith(prefix) and fields[field] is None:
                fields[field] = normalized.split(":", 1)[1].strip()

    registrar = fields["registrar"]
    created = fields["creation date"]
    expires = fields["registry expiry date"] or fields["expiration date"]

    details = []
    if registrar:
        details.append(f"registrar={registrar}")
    if created:
        details.append(f"created={created}")
    if expires:
        details.append(f"expires={expires}")

    if details:
        return f"WHOIS {domain}: " + " | ".join(details)

    if result.returncode != 0:
        return f"WHOIS lookup failed for {domain}"

    return f"WHOIS completed for {domain}, but no summary fields were found"


def ping(host: str) -> str:
    """Send four ICMP echo requests and return a summary."""
    host = host.strip().rstrip(".")

    if not _valid_target(host):
        return "Usage: !ping <hostname-or-ip>"

    executable = shutil.which("ping")
    if executable is None:
        return "Ping is unavailable inside the container"

    try:
        result = subprocess.run(
            [executable, "-c", "4", "-W", "2", host],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"Ping timed out for {host}"
    except OSError as error:
        return f"Ping failed: {error}"

    output = result.stdout or result.stderr
    packet_line = ""
    timing_line = ""

    for line in output.splitlines():
        if "packets transmitted" in line:
            packet_line = line.strip()
        elif "min/avg/max" in line:
            timing_line = line.strip()

    if packet_line and timing_line:
        return f"Ping {host}: {packet_line} | {timing_line}"

    if packet_line:
        return f"Ping {host}: {packet_line}"

    return f"Ping failed for {host}"


def trace(host: str) -> str:
    """Run a limited traceroute and return a compact hop summary."""
    host = host.strip().rstrip(".")

    if not _valid_target(host):
        return "Usage: !trace <hostname-or-ip>"

    executable = shutil.which("traceroute")
    if executable is None:
        return "Traceroute is unavailable inside the container"

    try:
        result = subprocess.run(
            [
                executable,
                "-m",
                "8",
                "-w",
                "2",
                "-q",
                "1",
                host,
            ],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"Traceroute timed out for {host}"
    except OSError as error:
        return f"Traceroute failed: {error}"

    lines = [
        line.strip()
        for line in result.stdout.splitlines()[1:]
        if line.strip()
    ]

    if not lines:
        return f"No traceroute results for {host}"

    hops = [" ".join(line.split()) for line in lines[:8]]
    return f"Trace {host}: " + " | ".join(hops)
