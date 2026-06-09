# Changelog

## v0.2.0

### Stronger behavior

- stopped relying only on raw `UNSEEN`; now the checker tracks processed UIDs to reduce duplicate digests
- added deterministic fallback summaries when the Anthropic call is unavailable or misconfigured
- made core logic more testable by separating UID filtering, state updates, digest formatting, and message collection
- added configurable limits for body and attachment previews

### Proof

- added unit tests for state handling, fallback summaries, digest formatting, and attachment extraction
- updated docs to reflect the new trust-oriented behavior
