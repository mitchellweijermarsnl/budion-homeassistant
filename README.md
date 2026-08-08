<p align="center">
  <img src="branding/icon.png" alt="Budion" width="128">
</p>

# Budion Home Assistant Integration

Home Assistant custom integration for [Budion](https://budion.app) — your family dashboard for meal planning, shopping lists, tasks, and birthdays.

## Features

This integration connects to the Budion API and exposes useful sensors for your Home Assistant dashboard:

| Sensor | Description |
|--------|-------------|
| **Ontbijt / Lunch / Avondeten / Snack** | What is planned for today (only enabled meal types; food icons follow Budion) |
| **Taken vandaag** | Open family tasks (with full task list in attributes) |
| **Verjaardagen** | Upcoming birthdays from contacts and family members |
| **Verjaardagen (kalender)** | Full birthday calendar with all names, including multiple on the same day |
| **Boodschappenlijsten** | One sensor per shopping list with open item count |
| **Gezin** | Family name and subscription feature flags |
| **Per kind** | Budcoin-saldo + open taken (tiener, kind, jong kind) |

All meal and task sensors include rich attributes for use in automations, templates, and custom cards.

## Requirements

- Home Assistant 2024.1 or newer (2026.3+ recommended for inline brand icons)
- A Budion account on [app.budion.com](https://app.budion.com) with **Premium** or **Pro** (meal planning, tasks, and contacts require paid features)

The integration connects automatically to Budion production — no URL configuration needed.

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

1. **Email & password** — your [app.budion.com](https://app.budion.com) account
2. **2FA code** — only if two-factor authentication is enabled
3. **Family selection** — only if your account belongs to multiple families

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

The sensor exposes `entity_picture` and an `image_url` attribute when the planned meal is linked to a recipe with a photo. Manual meals without a recipe photo use the Budion food icon (`icon` + `icon_mdi` attributes; the entity icon updates too).

For a larger photo with the title:

```yaml
type: picture-entity
entity: sensor.<family>_avondeten
name: Vanavond eten we
show_state: true
show_name: true
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

### Child budcoins and tasks

For each child (`teen`, `child`, `young_child`) with Premium features:

```yaml
type: horizontal-stack
cards:
  - type: entity
    entity: sensor.<family>_sam_budcoins
  - type: entity
    entity: sensor.<family>_sam_taken
```

Each child sensor also exposes the profile photo as `entity_picture` when available.

## Branding

The Budion logo is bundled in `custom_components/budion/brand/` so it appears in Home Assistant during setup, updates, and on the Integrations page (Home Assistant 2026.3+).

## Development

This integration connects to `https://api.budion.com` (production API for app.budion.com). The API uses Laravel Sanctum bearer tokens at `/api/v1/*`.

## Roadmap

- [ ] Dynamic discovery of new shopping lists / meal types without reload
- [ ] Todo list platform for shopping items
- [ ] Re-authentication flow when tokens expire

## License

MIT
