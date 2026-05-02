# CareScribe PRD — Medical Audio Transcription + Translation MVP

## Original Problem Statement
Build a 2-minute doctor-patient audio transcription and translation web app for medical use cases. Users should record or upload short audio, convert speech to transcript, optionally translate into English/Hindi/Punjabi, structure the medical prescription with an LLM, edit/copy/download/delete results, and keep audio temporary.

## Architecture Decisions
- Frontend: React app with route-based pages matching the requested flows: `/`, `/login`, `/record`, `/result/:id`, `/history`.
- Backend: FastAPI under `/api`, SQLite/SQLAlchemy database per user choice, JWT-style demo authentication.
- Database: `users`, `sessions`, and `transcripts` tables implemented with SQLAlchemy models.
- Audio: multipart upload to `/tmp`, max 25MB and 120-second validation; temporary file is deleted after processing.
- External AI: Sarvam STT/translation is now configured for live Sarvam use after explicit user approval. Gemini prescription extraction remains **MOCKED**.

## User Personas
- Doctor: records or uploads a short consultation and needs fast structured notes.
- Clinic assistant: reviews, edits, copies, downloads, or deletes generated medical text.
- Admin/tester: validates session history and protected workflows with a demo account.

## Core Requirements
- Public landing and login pages.
- Protected record, result, and history pages.
- Recorder/upload UI with clear states: idle, recording, uploading, processing, completed/failed.
- Language selection: source Auto/English/Hindi/Punjabi and output English/Hindi/Punjabi.
- Transcript, translation, structured prescription editor.
- Copy, download `.txt`, save edits, delete session.
- History table with view/delete actions.
- Edge handling for microphone denial, unsupported formats, too-large files, empty files, duplicate/busy processing states.

## Implemented — 2026-05-02
- Built complete frontend experience with warm medical UI, protected routes, login, recorder/upload, results editor, and history table.
- Built FastAPI backend with health, auth, sessions, audio upload, process, status, result fetch/update, history list, and delete endpoints.
- Added deterministic **MOCKED** Sarvam STT, **MOCKED** Sarvam translation, and **MOCKED** Gemini prescription extraction.
- Added SQLite persistence, demo doctor account, temporary audio cleanup, validation for format/size/duration, and result warnings.
- Fixed regression issues: clipboard permission crash, History dynamic test IDs/rendering, History delete error handling, Result delete error handling.
- Test credentials documented in `/app/memory/test_credentials.md`.

## Prioritized Backlog
### P0 Remaining
- Validate live Sarvam STT/translation with a real user audio sample.
- Replace **MOCKED** Gemini prescription extraction with live Gemini only after explicit user approval.

### P1 Remaining
- Add real audio duration probing server-side for uploaded files.
- Add background job timeout/zombie-state handling beyond current simulated processing.
- Add registration or multi-user administration if needed.

### P2 Remaining
- Add PDF export and clinic branding.
- Add structured prescription templates by specialty.
- Add search/filter in history.

## Next Tasks
1. When approved, wire live Sarvam Batch Speech-to-Text and Translation using the provided credential.
2. When approved, wire live Gemini prescription extraction.
3. Add richer prescription export formats and specialty-specific templates.

## Implemented — 2026-05-02 Update
- Enabled live Sarvam Batch Speech-to-Text and Sarvam text translation after explicit user approval.
- Kept Gemini prescription extraction **MOCKED** as previously requested.
- Verified backend health and login only; no live Sarvam transcription test was run so the user can try it first.

## Fixed — 2026-05-02 Sarvam Result Parsing
- Root cause: Sarvam Batch jobs were completing successfully, but the backend only read job metadata and did not download/parse the output JSON transcript file.
- Fix: backend now downloads Sarvam output JSON after job completion and stores the real `transcript`, `language_code`, and confidence.
- Repaired previously affected completed sessions that displayed “No speech detected” by pulling their completed Sarvam outputs without starting new transcription jobs.
- Gemini prescription extraction remains **MOCKED**.
