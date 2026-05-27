# Security Policy: Insights Explorer

We take the security of your private chats and local databases extremely seriously. Because **Insights Explorer** is built specifically to process and index highly personal conversation logs locally and offline, safeguarding your data boundaries is our primary design tenet.

---

## 🛡️ Supported Versions

We actively support and patch vulnerabilities on the following versions:

| Version | Supported          |
| ------- | ------------------ |
| v1.0.x  | :white_check_mark: |
| < v1.0  | :x:                |

---

## 🔒 Reporting a Vulnerability

If you identify a security vulnerability (such as a local data leak, improper secret handling, or path traversal bugs), **please do not open a public GitHub issue**. Instead, report it privately to ensure developer privacy.

### Contact Information
Please send your vulnerability reports privately to:
- **Email**: [security@idaneyal.com](mailto:security@idaneyal.com)

Please include as much detail as possible, including:
- A description of the vulnerability and its potential impact.
- Step-by-step instructions to reproduce the issue.
- Details of your local environment (OS, node/python versions, model configurations).

We will acknowledge receipt of your report within **48 hours** and provide a detailed timeline for addressing the issue.

---

## 🚫 Safe Practices & Boundaries
- **Keep Your Data Local**: Insights Explorer is designed to run entirely locally. Never expose your FastAPI server (`127.0.0.1:8000`) to the public internet unless you have configured secure authentication gateways.
- **Git Safety**: Verify that your `.env` and `chat.txt` are never added to source commits. Our hardened `.gitignore` will prevent this by default.
