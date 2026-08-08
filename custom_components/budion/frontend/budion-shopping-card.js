/**
 * Budion shopping list card (boodschappen UI on top of a todo entity).
 *
 * type: custom:budion-shopping-card
 * entity: todo.<family>_weekboodschappen
 * title: Boodschappen   # optional
 */
class BudionShoppingCard extends HTMLElement {
  static getStubConfig(hass) {
    const entity = Object.keys(hass.states || {}).find(
      (entityId) =>
        entityId.startsWith("todo.") &&
        (entityId.includes("boodschap") ||
          entityId.includes("shopping") ||
          entityId.includes("lijst")),
    );
    return {
      type: "custom:budion-shopping-card",
      entity: entity || "",
      title: "Boodschappen",
    };
  }

  static getConfigElement() {
    return document.createElement("budion-shopping-card-editor");
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Please define a todo entity");
    }
    this._config = {
      title: "Boodschappen",
      ...config,
    };
    this._items = [];
    this._ensureDom();
    this._render();
  }

  connectedCallback() {
    this._subscribe();
  }

  disconnectedCallback() {
    this._unsubscribe();
  }

  set hass(hass) {
    const entityChanged = this._hass?.states?.[this._config?.entity] !== hass?.states?.[this._config?.entity];
    this._hass = hass;
    if (entityChanged || !this._unsub) {
      this._subscribe();
    }
    this._render();
  }

  getCardSize() {
    return Math.min(Math.max((this._items?.length || 0) + 2, 3), 10);
  }

  _ensureDom() {
    if (this._card) {
      return;
    }
    this.innerHTML = "";
    this._card = document.createElement("ha-card");
    this.appendChild(this._card);
    const style = document.createElement("style");
    style.textContent = `
      ha-card { overflow: hidden; }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 16px 16px 10px;
      }
      .title-wrap {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
      }
      .cart {
        width: 34px;
        height: 34px;
        border-radius: 10px;
        display: grid;
        place-items: center;
        background: color-mix(in srgb, var(--primary-color, #03a9f4) 16%, transparent);
        color: var(--primary-color, #03a9f4);
        flex: 0 0 auto;
      }
      .title {
        font-size: 1.1rem;
        font-weight: 650;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .count {
        color: var(--secondary-text-color);
        font-size: 0.85rem;
        white-space: nowrap;
      }
      .add {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 8px;
        padding: 0 12px 12px;
      }
      .add input {
        width: 100%;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color);
        color: var(--primary-text-color);
        border-radius: 12px;
        padding: 12px 14px;
        font: inherit;
      }
      .add button, .row button {
        border: 0;
        border-radius: 12px;
        padding: 12px 14px;
        font: inherit;
        font-weight: 600;
        cursor: pointer;
      }
      .add button {
        background: var(--primary-color, #03a9f4);
        color: var(--text-primary-color, #fff);
      }
      .list { padding: 0 8px 12px; display: flex; flex-direction: column; }
      .row {
        display: grid;
        grid-template-columns: auto 1fr auto;
        gap: 10px;
        align-items: center;
        padding: 10px 8px;
        border-radius: 14px;
      }
      .row:hover { background: var(--secondary-background-color); }
      .row.done .name { text-decoration: line-through; opacity: 0.65; }
      .check {
        width: 22px;
        height: 22px;
        border-radius: 7px;
        border: 2px solid var(--primary-color, #03a9f4);
        display: grid;
        place-items: center;
        cursor: pointer;
        background: transparent;
        padding: 0;
      }
      .row.done .check {
        background: var(--primary-color, #03a9f4);
        color: white;
      }
      .name { font-weight: 600; }
      .qty {
        color: var(--secondary-text-color);
        font-size: 0.85rem;
        margin-top: 2px;
      }
      .delete {
        background: transparent;
        color: var(--secondary-text-color);
        padding: 8px 10px;
      }
      .empty, .error {
        padding: 18px 16px 22px;
        color: var(--secondary-text-color);
        text-align: center;
      }
    `;
    this.appendChild(style);
  }

  async _subscribe() {
    this._unsubscribe();
    if (!this._hass || !this._config?.entity || !this.isConnected) {
      return;
    }
    if (!this._hass.states[this._config.entity]) {
      this._items = [];
      this._render();
      return;
    }
    try {
      this._unsub = await this._hass.connection.subscribeMessage(
        (message) => {
          this._items = Array.isArray(message?.items) ? message.items : [];
          this._render();
        },
        {
          type: "todo/item/subscribe",
          entity_id: this._config.entity,
        },
      );
    } catch (_err) {
      this._items = [];
      this._render();
    }
  }

  _unsubscribe() {
    if (typeof this._unsub === "function") {
      this._unsub();
    }
    this._unsub = null;
  }

  _nl() {
    return String(this._hass?.locale?.language || "").startsWith("nl");
  }

  async _addItem(summary) {
    const value = String(summary || "").trim();
    if (!value || !this._hass) {
      return;
    }
    await this._hass.callService("todo", "add_item", {
      entity_id: this._config.entity,
      item: value,
    });
  }

  async _toggle(item) {
    if (!this._hass || !item?.uid) {
      return;
    }
    const next =
      item.status === "completed" ? "needs_action" : "completed";
    await this._hass.callService("todo", "update_item", {
      entity_id: this._config.entity,
      item: item.uid,
      status: next,
    });
  }

  async _remove(item) {
    if (!this._hass || !item?.uid) {
      return;
    }
    await this._hass.callService("todo", "remove_item", {
      entity_id: this._config.entity,
      item: item.uid,
    });
  }

  _render() {
    if (!this._config || !this._card) {
      return;
    }
    const nl = this._nl();
    const state = this._hass?.states?.[this._config.entity];
    const openItems = (this._items || []).filter((item) => item.status !== "completed");
    const doneItems = (this._items || []).filter((item) => item.status === "completed");
    const title =
      this._config.title ||
      state?.attributes?.friendly_name ||
      (nl ? "Boodschappen" : "Shopping");

    let body = `
      <div class="header">
        <div class="title-wrap">
          <div class="cart">
            <ha-icon icon="mdi:cart-outline"></ha-icon>
          </div>
          <div class="title">${this._escape(title)}</div>
        </div>
        <div class="count">${openItems.length} ${nl ? "open" : "open"}</div>
      </div>
    `;

    if (!state) {
      body += `<div class="error">${nl ? "Boodschappenlijst niet gevonden" : "Shopping list not found"}</div>`;
      this._card.innerHTML = body;
      return;
    }

    body += `
      <div class="add">
        <input id="budion-add" type="text" placeholder="${
          nl ? "Voeg boodschap toe…" : "Add grocery item…"
        }" />
        <button type="button" id="budion-add-btn">${nl ? "Toevoegen" : "Add"}</button>
      </div>
    `;

    if (!this._items.length) {
      body += `<div class="empty">${
        nl ? "Je lijst is nog leeg — voeg iets toe" : "Your list is empty — add something"
      }</div>`;
    } else {
      body += `<div class="list">`;
      for (const item of [...openItems, ...doneItems]) {
        const done = item.status === "completed";
        body += `
          <div class="row ${done ? "done" : ""}" data-uid="${this._escapeAttr(item.uid || "")}">
            <button class="check" type="button" data-action="toggle" aria-label="toggle">${
              done ? "✓" : ""
            }</button>
            <div>
              <div class="name">${this._escape(item.summary || "")}</div>
              ${
                item.description
                  ? `<div class="qty">${this._escape(item.description)}</div>`
                  : ""
              }
            </div>
            <button class="delete" type="button" data-action="delete" aria-label="delete">✕</button>
          </div>
        `;
      }
      body += `</div>`;
    }

    this._card.innerHTML = body;

    const input = this._card.querySelector("#budion-add");
    const addBtn = this._card.querySelector("#budion-add-btn");
    const submit = async () => {
      const value = input?.value || "";
      if (input) {
        input.value = "";
      }
      await this._addItem(value);
    };
    addBtn?.addEventListener("click", submit);
    input?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submit();
      }
    });

    this._card.querySelectorAll(".row").forEach((row) => {
      const uid = row.getAttribute("data-uid");
      const item = (this._items || []).find((entry) => entry.uid === uid);
      row.querySelector('[data-action="toggle"]')?.addEventListener("click", () => {
        this._toggle(item);
      });
      row.querySelector('[data-action="delete"]')?.addEventListener("click", () => {
        this._remove(item);
      });
    });
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

class BudionShoppingCardEditor extends HTMLElement {
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
        </div>
      `;
      this._title = this.querySelector("#title");
      this._entity = this.querySelector("#entity");
      this._entity.selector = { entity: { domain: "todo" } };
      this._title.addEventListener("change", () => this._changed());
      this._title.addEventListener("input", () => this._changed());
      this._entity.addEventListener("value-changed", (ev) => {
        this._config = { ...this._config, entity: ev.detail.value };
        this._fire();
      });
      this._built = true;
    }
    this._title.value = this._config.title || "Boodschappen";
    this._entity.value = this._config.entity || "";
    this._entity.hass = this._hass;
  }

  _changed() {
    this._config = { ...this._config, title: this._title.value };
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

customElements.define("budion-shopping-card", BudionShoppingCard);
customElements.define("budion-shopping-card-editor", BudionShoppingCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "budion-shopping-card",
  name: "Budion Boodschappen",
  description: "Boodschappenlijst-widget met afvinken en toevoegen",
  preview: true,
});
