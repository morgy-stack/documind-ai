# Security considerations

This repository is a portfolio implementation, not a security-certified product.

Before handling sensitive or customer data:
- Add authentication and authorization.
- Isolate document collections by user/tenant and enforce access checks on every operation.
- Scan uploads for malware and validate actual file content, not only filename extensions.
- Set reverse-proxy and application request-size limits.
- Add rate limiting, quotas, and abuse monitoring.
- Protect API keys with a secrets manager; never commit `.env`.
- Define retention, deletion, backup, and privacy procedures.
- Treat retrieved document content as untrusted prompt input.
- Review logging so confidential document text and credentials are not exposed.
