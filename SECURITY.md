# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.1.x | Yes |
| 1.0.x | Security fixes only |

---

## Reporting a vulnerability

Do not open a public GitHub issue for security vulnerabilities. This exposes the vulnerability to everyone before a fix is available.

Instead, send details to the maintainers via one of these channels:

- GitHub private security advisory: use the "Report a vulnerability" button on the Security tab of this repository.
- Email: if direct contact information is listed in `about/AUTHORS.md`, use it.

Please include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce it, or a proof-of-concept if you have one.
- The version(s) affected.
- Any suggested mitigations or fixes you have identified.

---

## What to expect

We will acknowledge receipt within 3 business days. We aim to release a fix within 30 days of confirmation, depending on severity. We will coordinate the disclosure timeline with you.

---

## Scope

ReasonTree handles user-supplied file paths, PDF content, and query text. These inputs are passed to LLM APIs and to PDF parsing libraries. Potential vulnerability areas include:

- Path traversal in file handling.
- Prompt injection via document content or query text.
- API key exposure via logging.
- Insecure deserialization of workspace JSON files.

Reports in any of these areas are welcome. Reports about the LLM providers themselves (OpenAI, Anthropic, etc.) should be directed to those organizations.
