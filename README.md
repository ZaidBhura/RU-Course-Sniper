# Rutgers Index Course Sniper

A production-quality Python application that monitors Rutgers course availability and sends instant notifications when watched index numbers become available.

## ⚠️ Important Notes

- **This tool does NOT automate enrollment.** It only detects availability and notifies you.
- **You must manually enroll** by clicking "Add Courses" in WebReg after receiving a notification.
- **Be respectful with polling intervals.** The default 20 seconds is reasonable. Don't set it below 10 seconds.

## Features

- ✅ Monitors specific 5-digit WebReg index numbers
- ✅ Instant notifications via Discord webhook (required)
- ✅ Optional Pushover notifications
- ✅ Automatic course detail enrichment (subject, course number, title, instructor, meeting times)
- ✅ WebReg links with prefilled index for quick enrollment
- ✅ **Interactive command interface** - Add/remove indexes while running
- ✅ Robust error handling with exponential backoff retries
- ✅ Graceful shutdown on Ctrl+C
- ✅ Clean console logging with timestamps

## Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Application

**Copy configuration files:**
```bash
copy config.yaml.example config.yaml
copy .env.example .env
```

These create your local runtime files. Keep `config.yaml` and `.env` private and out of Git.

**Edit `config.yaml`:**
- Set `poll_interval_seconds` (default: 20)
- Set `webreg_semester_selection` (default: "12026" for Spring 2026)
- Add your watched indexes under `watch_indexes`

**Edit `.env`:**
- Set `DISCORD_WEBHOOK_URL` (required)
- Optionally set `PUSHOVER_TOKEN` and `PUSHOVER_USER` for Pushover notifications

### 5. Get Discord Webhook URL

1. Open your Discord server
2. Go to Server Settings > Integrations > Webhooks
3. Click "New Webhook"
4. Copy the webhook URL
5. Paste it into `.env` as `DISCORD_WEBHOOK_URL`

### 6. Run the Application

```bash
cd rutgers_index_sniper
python -m src.main
```

The application will:
- Print startup information
- Begin polling every `poll_interval_seconds`
- Send notifications when watched indexes open
- Continue running until you press Ctrl+C

### Interactive Commands

While the application is running, you can use these commands in the terminal:

- `add <index> [label]` - Add an index to the watchlist
  - Example: `add 12345`
  - Example: `add 12345 "My Course"`
- `remove <index>` - Remove an index from the watchlist
  - Example: `remove 12345`
- `list` - Show all currently watched indexes and their status
- `help` - Show available commands
- `quit` or `exit` - Stop the application

## Configuration Format

### Simple Index (integer)
```yaml
watch_indexes:
  - 11643
  - 12345
```

### Index with Label (object)
```yaml
watch_indexes:
  - index: 11643
    label: "Preferred section"
  - index: 12345
    label: "Backup option"
```

You can mix both formats in the same configuration.

## How It Works

1. **Polling**: Every `poll_interval_seconds`, the application fetches the current open sections from Rutgers SOC API.

2. **State Tracking**: The application tracks which watched indexes are currently open and detects transitions from closed → open.

3. **Notifications**: When a watched index opens:
   - A notification is sent via Discord (and Pushover if configured)
   - The notification includes:
     - WebReg link with prefilled index (at the top for quick access)
     - Index number and optional label
     - Course details if available (subject, course number, section, title, instructor, meeting times)

4. **Enrichment**: Course details are fetched every 10 minutes and cached. If enrichment fails, notifications still fire with just the index number.

5. **Re-notification**: If an index closes and later reopens, you'll be notified again.

## Example Notification

When index 11643 opens, you'll receive a Discord message like:

```
🚨 INDEX 11643 IS NOW OPEN! 🚨

🔗 WebReg Link: https://sims.rutgers.edu/webreg/editSchedule.htm?login=cas&semesterSelection=12026&indexList=11643

Index: 11643 (Preferred section)
Course: CS 112 - 01
Title: Data Structures
Instructor(s): John Doe
Meeting Times: Mon/Wed 10:20 AM - 11:40 AM
```

## Troubleshooting

### "Configuration file not found"
- Make sure you copied `config.yaml.example` to `config.yaml`

### "No notifications sent"
- Check that `DISCORD_WEBHOOK_URL` is set in `.env`
- Verify your Discord webhook URL is correct
- Check Discord server permissions

### "Error during poll"
- Check your internet connection
- The application will retry automatically with exponential backoff
- If errors persist, the SOC API may be temporarily unavailable

### Notifications not appearing
- Check Discord webhook is still active (Discord > Server Settings > Integrations > Webhooks)
- Verify the webhook URL in `.env` is correct
- Check Discord server/channel permissions

## Project Structure

```
rutgers_index_sniper/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── config.yaml.example
├── test_api.py        # API inspection helper script
├── test_fix.py        # Manual debug script for open-section parsing
└── src/
    ├── main.py          # Entry point
    ├── soc_client.py    # API client with retry logic
    ├── watcher.py       # Main polling and state tracking
    ├── enricher.py      # Course detail caching
    ├── notifier.py      # Discord/Pushover notifications
    ├── models.py        # Data classes
    └── utils.py         # Configuration and helpers
```

## Technical Details

- **Python Version**: 3.10+
- **Dependencies**: requests, pyyaml, python-dotenv
- **API Endpoints**:
  - Open sections: `https://sis.rutgers.edu/soc/api/openSections.json`
  - Course details: `https://sis.rutgers.edu/soc/api/courses.json`
- **Request Timeout**: 10 seconds
- **Max Retries**: 3 with exponential backoff
- **Enrichment Cache**: Refreshed every 10 minutes

## License

This project is provided as-is for educational purposes. Use responsibly and in accordance with Rutgers University policies.

