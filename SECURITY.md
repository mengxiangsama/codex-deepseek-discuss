# Security

Do not include credentials, private code, or personal records in public issues.
For a suspected vulnerability, use the repository's private vulnerability report
feature if enabled. If unavailable, open a minimal issue asking for a private
reporting channel without disclosing exploit details or secrets.

The server sends the supplied prompt and a fixed system instruction to the
official DeepSeek API. It has no file-reading tool, arbitrary command tool, or
Harness backend. It reads one configured environment credential or its own
macOS Keychain item. Credential setup invokes a bundled Swift helper with the
secret on stdin, not argv. HTTP error bodies are not returned to the host.

The host chooses the prompt; this integration is not a data-loss-prevention
filter. A model answer must not be treated as permission to execute commands.
Hosts and providers may retain prompts and answers independently of this server.
HTTPX proxy settings are honored; use only trusted proxies and trust stores.

Do not configure credentials inside tracked files. Revoke leaked credentials at
the provider, including test credentials. The included scanner catches common
literal keys and private-key headers; it is not a complete secret detector.
