/*
 * Just enough DOM to run the report views outside a browser.
 *
 * The three views are pure functions of one response: payload in, element tree out.  That
 * makes them testable without a browser, which matters because AGENTS.md keeps the browser
 * suite a plus rather than a gate — the rules that must always hold should be checkable in
 * the default run.  What the browser suite (T20) covers is what this cannot: layout,
 * scrolling, focus, and whether anything is actually visible.
 *
 * This implements only what the views touch, and it is deliberately literal: an element
 * records what was set on it and nothing interprets it.  A view that started relying on
 * real layout or real CSS would fail here rather than silently passing.
 */

class ClassList {
  constructor(element) {
    this.element = element;
  }

  toggle(name, force) {
    const names = new Set(String(this.element.className || "").split(/\s+/).filter(Boolean));
    const wanted = force === undefined ? !names.has(name) : Boolean(force);
    if (wanted) names.add(name);
    else names.delete(name);
    this.element.className = [...names].join(" ");
  }

  add(...names) {
    for (const name of names) this.toggle(name, true);
  }

  remove(...names) {
    for (const name of names) this.toggle(name, false);
  }

  contains(name) {
    return String(this.element.className || "").split(/\s+/).includes(name);
  }
}

class Element {
  constructor(tag, namespace = null) {
    this.tagName = tag;
    this.namespace = namespace;
    this.className = "";
    this.children = [];
    this.attributes = new Map();
    this.listeners = new Map();
    this.ownText = "";
    this.classList = new ClassList(this);
    this.style = { properties: new Map(), setProperty: (n, v) => this.style.properties.set(n, v) };
    this._disabled = false;
    // `dataset` writes through to the attribute, the way the real one does, so a view can
    // set it either way and `[data-*]` selectors still find it.
    this.dataset = new Proxy(
      {},
      {
        get: (_target, name) => this.attributes.get(`data-${dashed(name)}`),
        set: (_target, name, value) => {
          this.attributes.set(`data-${dashed(name)}`, String(value));
          return true;
        },
        has: (_target, name) => this.attributes.has(`data-${dashed(name)}`),
      },
    );
  }

  set textContent(value) {
    this.ownText = String(value);
    this.children = [];
  }

  get textContent() {
    return this.ownText + this.children.map((child) => child.textContent).join("");
  }

  append(...nodes) {
    for (const child of nodes) this.children.push(child);
  }

  replaceChildren(...nodes) {
    this.children = [...nodes];
  }

  set disabled(value) {
    this._disabled = Boolean(value);
    if (this._disabled) this.attributes.set("disabled", "");
    else this.attributes.delete("disabled");
  }

  get disabled() {
    return this._disabled;
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  getAttribute(name) {
    return this.attributes.has(name) ? this.attributes.get(name) : null;
  }

  addEventListener(type, handler) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(handler);
  }

  /** Fire every handler registered for `type`, so highlighting can be exercised. */
  dispatch(type) {
    for (const handler of this.listeners.get(type) ?? []) handler({});
  }

  /** `.class`, `tag`, and `[attr]` — the three forms the views actually use. */
  matches(selector) {
    if (selector.startsWith("[") && selector.endsWith("]")) {
      return this.attributes.has(selector.slice(1, -1));
    }
    if (selector.startsWith(".")) return this.classList.contains(selector.slice(1));
    return this.tagName === selector;
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] ?? null;
  }

  querySelectorAll(selector) {
    const found = [];
    for (const child of this.children) {
      if (child.matches(selector)) found.push(child);
      found.push(...child.querySelectorAll(selector));
    }
    return found;
  }

  /** A plain tree, which is what the test assertions read. */
  toJSON() {
    return {
      tag: this.tagName,
      class: this.className || undefined,
      attrs: Object.fromEntries(this.attributes),
      style: Object.fromEntries(this.style.properties),
      text: this.textContent,
      ownText: this.ownText || undefined,
      children: this.children.map((child) => child.toJSON()),
    };
  }
}

function dashed(name) {
  return String(name).replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
}

export function install() {
  globalThis.document = {
    createElement: (tag) => new Element(tag),
    createElementNS: (namespace, tag) => new Element(tag, namespace),
  };
}
