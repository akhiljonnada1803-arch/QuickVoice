# Changelog

This file records user-visible and contributor-visible changes to QuickVoice. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and released versions will use semantic version numbers where practical.

QuickVoice has not published a stable release. Everything under `Unreleased` may change before the first tag.

## Unreleased

- Langfuse SDK integration with SDK v4.x observation API and SDK v2/v3 compatibility.
- Top-level `voice_call` root trace initialization with per-call context and multi-tenant tagging.
- `stt_recognition` spans for audio transcription timing and model tracking.
- `tool:<tool_name>` spans for HTTP and MCP tool execution monitoring.
- `rag_retrieval` spans for Knowledge Base search query and match metrics.
- LLM generation recording (`record_llm_generation`) with prompt/completion logging, model tracking, and token usage statistics.
- Score recording (`record_score`) for evaluation feedback and user metrics.
- Non-blocking asynchronous telemetry batch flushing (`flush_async`).
- Multi-environment file loader (`.env.local`, `.env.dev`, `.env`) with automated fallback and zero-PII privacy controls.
- Comprehensive error handling to prevent telemetry failures from interrupting call execution.
- Project governance, maintainer responsibilities, support boundaries, and a public roadmap.
- Structured GitHub issue forms for bugs, setup failures, documentation gaps, and feature proposals.
- A contributor assignment and duplicate-work policy.
- Release-readiness guidance and draft v0.1.0 release notes with known limitations.
- Fifteen credential-free starter issue drafts with acceptance and verification criteria.

### Changed

- Raised the documented and enforced minimum Node.js version from 18 to 20.9.
- Clarified Linux, macOS, and Windows/WSL2 setup paths.
- Replaced the generated Next.js console README with QuickVoice-specific setup and verification guidance.

### Security

- Issue and support guidance directs vulnerability details to private reporting and warns contributors not to publish credentials, recordings, transcripts, phone numbers belonging to real people, or customer data.

## Release History

No tagged release has been published. See the [v0.1.0 draft release notes](./docs/releases/v0.1.0-draft.md); that document is a release candidate draft, not evidence that v0.1.0 exists.
