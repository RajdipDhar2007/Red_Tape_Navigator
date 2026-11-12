# Security Policy

Red Tape Navigator handles sensitive information (identity numbers, business details and uploaded documents), so we take security reports seriously.

## Reporting a vulnerability

**Please do not open a public issue for a security problem.**

1. Use GitHub's **private vulnerability reporting**: open the repository's **Security** tab and choose **Report a vulnerability** (when it is enabled), or
2. contact the repository owner privately through GitHub: **RajdipDhar2007**, and ask for a private way to share the details.

Please include:

- what you found and where (file, endpoint or page);
- steps to reproduce, and the impact you believe it has;
- the version or commit you tested;
- whether you have shared it with anyone else.

Please use **test accounts and fake data only**. Do not access, change or keep other people's data, and do not run tests that degrade the service for others.

## What to expect

- We aim to acknowledge a report within **3 working days**.
- We aim to give a first assessment within **10 working days**, and to keep you informed until it is fixed.
- We will credit you in the fix notes if you wish. We cannot offer a paid bounty.

## Supported versions

The project is pre-launch. Only the latest commit on `main` is supported, and fixes land there first.

## Scope

In scope: the backend API, the web app, the build and deployment files in this repository, and how personal data is stored and protected.

Out of scope: third-party services we integrate with (report those to the provider), social engineering of team members, denial-of-service testing, and vulnerabilities that need physical access to a user's device.

## How the project protects data

Encryption of Aadhaar, PAN and bank answers at rest, rotating refresh tokens with reuse detection, account lockout, rate limiting, signed provider webhooks, an allowlist for outbound fetching, a hash-chained audit log, redaction before any model call, and dependency and secret scans in CI. The full list, mapped to the OWASP categories, is in [`docs/SECURITY.md`](docs/SECURITY.md); the threat model is in [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).

## If you find secrets

If you notice a key, password or token in the repository or its history, report it privately as above. Do not use it.
