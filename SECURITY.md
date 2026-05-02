# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

Craft Memory is a local development tool that stores data in a local SQLite database.
It does not process user data from external sources by default.

However, if you discover a security vulnerability:

1. **Do not open a public issue.**
2. Send a description of the vulnerability to the maintainer via GitHub Security Advisories:
   https://github.com/matrixNeo76/craft-memory/security/advisories/new
3. You will receive a response within 48 hours.
4. If the vulnerability is accepted, a fix will be prepared and released as soon as possible.

## Scope

The following are considered security-relevant:
- Remote code execution via MCP tool arguments
- Unauthorized access to the SQLite database
- Injection attacks via FTS5 search queries
- Information disclosure through error messages

The following are out of scope:
- Denial of service via large payloads (local tool)
- Physical access to the machine running the server
