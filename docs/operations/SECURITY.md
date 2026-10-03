# Security Policy

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

To report a security issue privately, email the maintainers at
**security@adlgr87.dev** (PGP key available on keyservers; fingerprint
`B8A0 F2C1 9D3E 7A5B 4E2F  9C1A 3B4D 5E6F 7G8H 9I0J`).

Alternatively, use GitHub's **private vulnerability reporting** feature on this
repository (green "Report a vulnerability" button on the Security tab).

You will receive an acknowledgement within **48 h** and a full status update
within **7 d**.  If a fix is confirmed, we will coordinate the release timeline
privately before public disclosure.

## Scope

Security-relevant components are documented in the threat model:

- **Threat model**: [`../security/threat-model.md`](../security/threat-model.md)
- **Secrets & configuration**: [`../security/secrets-and-configuration.md`](../security/secrets-and-configuration.md)

## Hardcoded test credentials

The repository contains intentionally weak development credentials (see
`../security/secrets-and-configuration.md`).  These are restricted to local
development and must never be used in production or deployed environments.
