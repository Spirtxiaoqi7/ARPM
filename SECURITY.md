# Security Policy

## Supported Versions

ARPM is a research-oriented open-source project. Security fixes are handled on the default branch unless a release branch is explicitly announced.

## Reporting a Vulnerability

Please do not open a public issue for secrets, authentication problems, data leaks, or vulnerabilities that could expose private dialogue logs.

Report privately by contacting the repository owner through GitHub. Include:

- affected commit or version;
- operating system and deployment method;
- reproduction steps;
- expected impact;
- relevant logs with API keys and personal data removed.

## Sensitive Data Guidelines

- Do not commit API keys, provider tokens, private chat logs, local runtime databases, uploaded knowledge bases, or embedding model weights.
- Remove secrets from screenshots before opening issues.
- Keep `runtime/`, `assets/models/`, `.env`, and local logs outside commits.
