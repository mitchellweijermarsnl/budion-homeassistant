/**
 * Budion upcoming-birthdays agenda card.
 *
 * type: custom:budion-birthdays-card
 * entity: sensor.<family>_verjaardagen
 * title: Verjaardagen   # optional
 * max_items: 10         # optional
 */
class BudionBirthdaysCard extends HTMLElement {
  static getStubConfig(hass) {
    const entity = Object.keys(hass.states || {}).find(
      (entityId) =>
        entityId.startsWith("sensor.") &&
        (entityId.endsWith("_verjaardagen") ||
          entityId.endsWith("_upcoming_birthdays") ||
          entityId.includes("verjaardagen") ||
          entityId.includes("upcoming_birthdays")),
    );
    return {
      type: "custom:budion-birthdays-card",
      entity: entity || "",
      title: "Verjaardagen",
    };
  }

  static getConfigElement() {
    return document.createElement("budion-birthdays-card-editor");
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Please define an entity");
    }
    this._config = {
      title: "Verjaardagen",
      max_items: 0,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    const items = this._birthdays();
    return Math.min(Math.max(items.length + 1, 2), 8);
  }

  _birthdays() {
    if (!this._hass || !this._config?.entity) {
      return [];
    }
    const state = this._hass.states[this._config.entity];
    const birthdays = state?.attributes?.birthdays;
    if (!Array.isArray(birthdays)) {
      return [];
    }
    const maxItems = Number(this._config.max_items) || 0;
    return maxItems > 0 ? birthdays.slice(0, maxItems) : birthdays;
  }

  _formatRelative(daysUntil, locale) {
    if (daysUntil === 0) {
      return locale?.language?.startsWith("nl") ? "Vandaag" : "Today";
    }
    if (daysUntil === 1) {
      return locale?.language?.startsWith("nl") ? "Morgen" : "Tomorrow";
    }
    if (locale?.language?.startsWith("nl")) {
      return `Over ${daysUntil} dagen`;
    }
    return `In ${daysUntil} days`;
  }

  _formatDate(value, locale) {
    if (!value) {
      return "";
    }
    const date = new Date(`${value}T12:00:00`);
    try {
      return new Intl.DateTimeFormat(locale?.language || undefined, {
        weekday: "short",
        day: "numeric",
        month: "short",
      }).format(date);
    } catch (_err) {
      return value;
    }
  }

  _initials(name) {
    return String(name || "?")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || "")
      .join("");
  }

  _render() {
    if (!this._config) {
      return;
    }

    if (!this._card) {
      this.innerHTML = "";
      this._card = document.createElement("ha-card");
      this.appendChild(this._card);
      const style = document.createElement("style");
      style.textContent = `
        ha-card {
          overflow: hidden;
        }
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 16px 16px 8px;
        }
        .title {
          font-size: 1.1rem;
          font-weight: 600;
          letter-spacing: 0.01em;
        }
        .count {
          color: var(--secondary-text-color);
          font-size: 0.85rem;
        }
        .list {
          display: flex;
          flex-direction: column;
          padding: 4px 8px 12px;
        }
        .row {
          display: grid;
          grid-template-columns: 48px 1fr auto;
          gap: 12px;
          align-items: center;
          padding: 10px 8px;
          border-radius: 14px;
        }
        .row:hover {
          background: var(--secondary-background-color);
        }
        .avatar {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          object-fit: cover;
          background: linear-gradient(145deg, #ff7eb6, #ff0072);
          color: white;
          display: grid;
          place-items: center;
          font-weight: 700;
          font-size: 0.95rem;
          box-shadow: 0 4px 14px rgba(255, 0, 114, 0.22);
        }
        .avatar img {
          width: 100%;
          height: 100%;
          border-radius: 50%;
          object-fit: cover;
          display: block;
        }
        .meta {
          min-width: 0;
        }
        .name {
          font-weight: 600;
          font-size: 1rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .sub {
          color: var(--secondary-text-color);
          font-size: 0.85rem;
          margin-top: 2px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .badge {
          min-width: 72px;
          text-align: center;
          padding: 8px 10px;
          border-radius: 999px;
          background: color-mix(in srgb, #ff0072 14%, transparent);
          color: var(--primary-text-color);
          font-size: 0.78rem;
          font-weight: 650;
          line-height: 1.2;
        }
        .badge.today {
          background: #ff0072;
          color: white;
        }
        .empty {
          padding: 20px 16px 24px;
          color: var(--secondary-text-color);
          text-align: center;
        }
      `;
      this.appendChild(style);
    }

    const locale = this._hass?.locale || {};
    const birthdays = this._birthdays();
    const stateObj = this._hass?.states?.[this._config.entity];
    const nl = String(locale.language || "").startsWith("nl");

    let body = `
      <div class="header">
        <div class="title">${this._escape(this._config.title || "Verjaardagen")}</div>
        <div class="count">${birthdays.length}${nl ? " komend" : " upcoming"}</div>
      </div>
    `;

    if (!stateObj) {
      body += `<div class="empty">${nl ? "Entity niet gevonden" : "Entity not found"}</div>`;
    } else if (!birthdays.length) {
      body += `<div class="empty">${
        nl ? "Geen aankomende verjaardagen in deze periode" : "No upcoming birthdays in this period"
      }</div>`;
    } else {
      body += `<div class="list">`;
      for (const item of birthdays) {
        const days = Number(item.days_until);
        const relative = this._formatRelative(days, locale);
        const dateLabel = this._formatDate(item.next_occurrence, locale);
        const agePart =
          item.age != null
            ? nl
              ? ` · wordt ${item.age}`
              : ` · turns ${item.age}`
            : "";
        const badgeClass = days === 0 ? "badge today" : "badge";
        const avatar = item.image_url
          ? `<div class="avatar"><img src="${this._escapeAttr(item.image_url)}" alt="" loading="lazy" /></div>`
          : `<div class="avatar">${this._escape(this._initials(item.name))}</div>`;

        body += `
          <div class="row">
            ${avatar}
            <div class="meta">
              <div class="name">${this._escape(item.name || "")}</div>
              <div class="sub">${this._escape(dateLabel)}${this._escape(agePart)}</div>
            </div>
            <div class="${badgeClass}">${this._escape(relative)}</div>
          </div>
        `;
      }
      body += `</div>`;
    }

    this._card.innerHTML = body;
  }

  _escape(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  _escapeAttr(value) {
    return this._escape(value).replaceAll("'", "&#39;");
  }
}

class BudionBirthdaysCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._config) {
      return;
    }
    if (!this._built) {
      this.innerHTML = `
        <div class="form">
          <ha-textfield id="title" label="Title" style="width:100%;margin-bottom:12px;"></ha-textfield>
          <ha-selector id="entity"></ha-selector>
          <ha-textfield id="max_items" label="Max items (0 = all)" type="number" style="width:100%;margin-top:12px;"></ha-textfield>
        </div>
      `;
      this._title = this.querySelector("#title");
      this._entity = this.querySelector("#entity");
      this._max = this.querySelector("#max_items");
      this._entity.selector = { entity: { domain: "sensor" } };
      this._title.addEventListener("change", () => this._changed());
      this._title.addEventListener("input", () => this._changed());
      this._entity.addEventListener("value-changed", (ev) => {
        this._config = { ...this._config, entity: ev.detail.value };
        this._fire();
      });
      this._max.addEventListener("change", () => this._changed());
      this._max.addEventListener("input", () => this._changed());
      this._built = true;
    }
    this._title.value = this._config.title || "";
    this._entity.value = this._config.entity || "";
    this._entity.hass = this._hass;
    this._max.value = String(this._config.max_items ?? 0);
  }

  _changed() {
    this._config = {
      ...this._config,
      title: this._title.value,
      max_items: Number(this._max.value || 0),
    };
    this._fire();
  }

  _fire() {
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }),
    );
  }
}

customElements.define("budion-birthdays-card", BudionBirthdaysCard);
customElements.define("budion-birthdays-card-editor", BudionBirthdaysCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "budion-birthdays-card",
  name: "Budion Birthdays",
  description: "Agenda widget for upcoming Budion birthdays with photos",
  preview: true,
});
