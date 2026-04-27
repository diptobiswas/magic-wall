# Security

Magic Wall is a local-first Raspberry Pi app. It does not run a hosted service and does not need a Magic Wall account.

## Secrets

Do not commit:

- OpenAI API keys
- `~/.config/magic-wall/config.toml`
- `.env` files
- generated images or runtime state
- local logs

The repository `.gitignore` excludes local runtime folders such as `.venv/`, `magic-wall-data/`, caches, build artifacts, and coverage output.

## Runtime Network Access

Magic Wall is designed to use only OpenAI API calls at runtime:

- OpenAI web search for story discovery
- OpenAI image generation for the wallpaper

## Reporting Issues

If you find a security issue, please open a private advisory on GitHub if available, or contact the repository owner directly.
