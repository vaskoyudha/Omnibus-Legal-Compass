# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| v2.x    | :white_check_mark: |
| < v2.0  | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please send an e-mail to security@omnibus-legal.dev. All security vulnerabilities will be promptly addressed.

Please do NOT open public GitHub issues for security vulnerabilities.

## Responsible Disclosure

We follow a 90-day responsible disclosure timeline. We ask that you do not share the vulnerability publicly until we have had a chance to fix it and release a new version.

## Known Past Issues

In February 2026, a `.env` file containing an API key was accidentally committed to the repository. This file has since been purged from the git history, and the affected key has been rotated.

## Security Best Practices

Contributors are reminded to:
- Never commit `.env` files or any other secrets.
- Ensure pre-commit hooks are installed and running to catch potential secret leaks.
- Keep dependencies updated to their latest secure versions.
