# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

WeRead Playwright is a Python automation tool that uses Playwright to simulate reading sessions on WeRead (weread.qq.com), a Chinese e-book platform. The project automatically logs in via QR code, selects books, and simulates reading behavior with configurable timing and notifications.

## Development Commands

### Setup
```bash
# Install dependencies and browser
uv sync
uv run playwright install chromium
```

**Requirements**: Python >=3.12. Uses `uv` for dependency management (see pyproject.toml).

### Running the application
```bash
# Run once immediately
uv run python main.py

# Run with scheduled mode (requires WEREAD_SCHEDULE_ENABLED=true in .env)
uv run python main.py
```

### Docker

**Using Docker Compose (Recommended):**

```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

**Using the build script (supports multi-platform builds):**

```bash
# Default build (linux/amd64)
./build.sh

# Build for specific platform
./build.sh --platform linux/arm64

# Multi-platform build and push to registry
./build.sh --platform linux/amd64,linux/arm64 --push

# Custom name and tag
./build.sh --name my-weread --tag v1.0
```

**Using Docker commands directly:**

```bash
# Build image
docker build -t weread-playwright .

# Run with environment variables
docker run -d \
  -v $(pwd)/data:/app/data \
  -e WEREAD_HEADLESS=true \
  -e WEREAD_BOOK_IDS=your_book_id \
  -e WEREAD_DURATION=30 \
  -e WEREAD_EMAIL_ENABLED=true \
  -e WEREAD_EMAIL_SMTP=smtp.gmail.com \
  -e WEREAD_EMAIL_PORT=587 \
  -e WEREAD_EMAIL_FROM=your-email@gmail.com \
  -e WEREAD_EMAIL_TO=recipient@gmail.com \
  -e WEREAD_EMAIL_PASSWORD=your-password \
  weread-playwright

# Run with .env file
docker run -d \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  weread-playwright

# Run in scheduled mode
docker run -d \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  -e WEREAD_SCHEDULE_ENABLED=true \
  -e WEREAD_SCHEDULE_CRON="0 9 * * *" \
  weread-playwright
```

**Important**: Mount the `data/` volume to persist cookies and statistics across container restarts.

### Configuration
Copy `env.example` to `.env` and configure environment variables. The application uses environment variables to override default configuration.

## Architecture

### Core Components

The application follows a modular architecture with clear separation of concerns:

**main.py**: Entry point that orchestrates the reading session workflow
- Creates the `data/` directory for storing cookies and stats
- Initializes configuration, logger, and core components
- Manages the browser lifecycle using Playwright's async context managers
- Handles both immediate execution and scheduled mode via APScheduler

**weread/config.py**: Configuration management with environment variable overrides
- Provides default configuration as nested dictionaries
- Maps environment variables (WEREAD_*) to configuration keys
- Uses dot notation for nested key access (e.g., "browser.headless")

**weread/auth.py**: Authentication and session management
- Handles QR code login flow with automatic refresh
- Persists cookies to `data/cookies.json` for subsequent sessions
- Takes screenshot of QR code and optionally emails it via Notifier
- Waits for login success by detecting "我的书架" (My Bookshelf) text

**weread/reader.py**: Core reading automation logic
- Selects book from configured book IDs (random selection)
- Simulates reading by clicking "下一章"/"下一页" buttons or pressing ArrowDown
- Handles edge cases: book completion, retry prompts, subscription walls
- Automatically jumps back to first chapter when book is finished
- Uses random sleep intervals to simulate human reading behavior
- **Important**: The `read()` method returns a tuple `(pages_read, actual_minutes)` - always track actual reading time, not configured duration

**weread/notifier.py**: Multi-channel notification system
- Email notifications with SMTP (SSL/TLS/auto-detection based on port)
- Bark push notifications (iOS push service)
- Supports sending QR code as email attachment during login

**weread/scheduler.py**: Cron-based task scheduling
- Wraps APScheduler's AsyncIOScheduler
- Uses standard cron expressions for scheduling

**weread/stats.py**: Reading session statistics tracking
- Persists session data to `data/stats.json`
- Tracks total sessions, pages read, and reading time
- Records individual session details (date, book, pages, duration)
- **Important**: Always use actual reading time (measured from start to end of session) for statistics, not the configured duration

### Data Flow

1. **Initialization**: Config loads defaults → applies env overrides → creates logger
2. **Authentication**: Load cookies → navigate to WeRead → QR login (if needed) → save cookies
3. **Reading Session**: Select book by ID → navigate to reader page → simulate reading for configured duration → track stats
4. **Completion**: Send notifications (email/Bark) → close browser → persist stats

### Configuration System

The Config class uses a two-tier system:
- Default configuration in `_default_config()` method
- Environment variable overrides via `_apply_env_overrides()`

All environment variables follow the pattern `WEREAD_*` and map to nested config keys:
- `WEREAD_HEADLESS` → `browser.headless`
- `WEREAD_EMAIL_SMTP` → `notifications.email.smtp_server`
- `WEREAD_BOOK_IDS` → `reading.book_ids` (comma-separated list)

### Browser Automation Strategy

The application uses Playwright's async API with Chromium:
- Runs with Chrome channel for better compatibility
- Uses specific selectors for WeRead's UI elements
- Implements retry logic for QR code expiration
- Handles page reloads on errors
- Simulates human-like behavior with random timing

**Async/Await Pattern**: All browser operations use async/await. The main entry point is `async def main()` which runs via `asyncio.run()`. Reading sessions are executed in `async def run_reading_session()`.

### File Storage

All persistent data is stored in the `data/` directory:
- `data/cookies.json`: Browser cookies for session persistence
- `data/stats.json`: Reading session statistics
- `data/qr_code.png`: Login QR code screenshot (temporary)
- `weread.log`: Application logs

**Important**: The `data/` directory is created automatically at startup if it doesn't exist. When using Docker, always mount this directory as a volume to persist data across container restarts.

## Email Configuration Notes

The email system auto-detects encryption based on port:
- Port 465: Uses SSL (SMTP_SSL)
- Port 587: Uses TLS (STARTTLS)
- Can be overridden with `WEREAD_EMAIL_SECURITY` (ssl/tls/none/auto)

Common SMTP configurations are documented in README.md for Gmail, QQ Mail, and 163 Mail.

## Important Implementation Patterns

### Measuring Actual vs. Configured Time
When tracking reading time or any duration-based metrics, always measure elapsed time rather than using configured values:

```python
# Correct pattern
start_time = datetime.now()
# ... do work ...
actual_minutes = (datetime.now() - start_time).total_seconds() / 60
stats.add_session(book, pages, actual_minutes)

# Incorrect pattern
duration = config.get("reading.duration_minutes", 30)
# ... do work ...
stats.add_session(book, pages, duration)  # Always uses configured time, not actual
```

### Config Value Access
The Config class uses dot notation for nested access:
- `config.get("browser.headless")` returns nested values
- Environment variables like `WEREAD_HEADLESS` map to `browser.headless`
- Converters handle type coercion (e.g., string to boolean, comma-separated string to list)

### Error Handling in Browser Automation
- Always use `try/except` around Playwright operations
- Use `await page.reload()` to recover from transient errors
- Check element counts with `await locator.count() > 0` before acting
- Use visibility checks with `await locator.is_visible()` for conditional logic
