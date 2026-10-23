# Medjugorje Messages

Private seven-language PWA prototype for the translation community. Vue 3 + Vuetify 3, GitHub Actions and offline-ready JSON archive.

**Status:** research archive awaiting editorial validation. No public deployment.

## From an Android phone

For remote development without GitHub Codespaces, use **Codex Cloud** with the GitHub repository:

- [Set up Codex Cloud](docs/CODEX_CLOUD.md) — publish a reusable environment and submit coding tasks
- [Instructions for Codex](AGENTS.md) — project rules, testing and content integrity
- [Test the PWA privately](docs/TESTING_PREVIEW.md) — legacy Codespaces preview steps if needed

## Validation

```bash
bash scripts/setup-cloud.sh
```

This runs npm/Python installations, JSON SHA-256 integrity verification, parser unit tests and Vue production build. For UI development `npm run dev` starts Vite on port `5173` under `/medjugorje-messages/`. Successful build does not itself prove Android installation or offline support.

Official date and community RSS monitoring are read-only review signals; they never auto-publish translated texts.
