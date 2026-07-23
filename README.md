<p align="center">
  <img src="branding/icon.png" alt="Budion" width="128">
</p>

# Budion Home Assistant Integration

Home Assistant custom integration for [Budion](https://budion.app) — your family dashboard for meal planning, shopping lists, tasks, and birthdays.

## Features

This integration connects to the Budion API and exposes useful sensors for your Home Assistant dashboard:

| Sensor | Description |
|--------|-------------|
| **Ontbijt / Lunch / Avondeten / Snack** | What is planned for today |
| **Taken vandaag** | Open family tasks (with full task list in attributes) |
| **Verjaardagen** | Upcoming birthdays from contacts and family members |
| **Boodschappenlijsten** | One sensor per shopping list with open item count |
| **Gezin** | Family name and subscription feature flags |

All meal and task sensors include rich attributes for use in automations, templates, and custom cards.

## Requirements

- Home Assistant 2024.1 or newer
- A Budion account with a **Premium** or **Pro** subscription (meal planning, tasks, and contacts require paid features)
- Your Budion instance URL (e.g. `https://budion.test` locally or your production URL)

## Installation

### Manual

1. Copy the `custom_components/budion` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Budion**.

### HACS (recommended)

1. Add this repository as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/) in HACS.
2. Install **Budion** from the Integrations category.
3. Restart Home Assistant and add the integration via the UI.

## Configuration

During setup you will be asked for:

1. **Budion URL** — the base URL of your Budion instance
2. **Email & password** — your Budion account credentials
3. **2FA code** — only if two-factor authentication is enabled
4. **Family selection** — only if your account belongs to multiple families

A long-lived API token is created and stored securely in Home Assistant.

### Options

After setup, you can configure the **update interval** (60–3600 seconds, default 300) via the integration options.

## Example dashboard cards

### Today's dinner

```yaml
type: entity
entity: sensor.<family>_avondeten
name: Vanavond eten we
```

### Open tasks

```yaml
type: entity
entity: sensor.<family>_taken_vandaag
name: Open taken
```

Use the `tasks` attribute in a Markdown or template card for a full list.

### Shopping list

```yaml
type: entity
entity: sensor.<family>_weekboodschappen
name: Boodschappen
```

The `open_items` attribute contains all unchecked items.

## Development

This integration lives alongside the Budion API project. The API uses Laravel Sanctum bearer tokens at `/api/v1/*`.

To test locally with [Laravel Herd](https://herd.laravel.com):

```
URL: https://budion.test
```

## Roadmap

- [ ] Calendar entities for meal plan and birthdays
- [ ] Dynamic discovery of new shopping lists
- [ ] Todo list platform for shopping items
- [ ] Re-authentication flow when tokens expire

## License

MIT
