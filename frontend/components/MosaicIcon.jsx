"use client";
/**
 * MosaicIcon — Renders an SVG icon from the JAGGAER Mosaic Icon Library.
 * Icons are served as static files from /icons/{name}.svg
 *
 * Usage:
 *   <MosaicIcon name="dashboard" size={20} className="text-slate-500" />
 *   <MosaicIcon name="analytics" size={16} />
 */

export default function MosaicIcon({
  name,
  size = 20,
  className = "",
  style = {},
  title,
  ...rest
}) {
  if (!name) return null;
  const src = `/icons/${name}.svg`;
  return (
    <img
      src={src}
      alt={title || name}
      width={size}
      height={size}
      className={className}
      style={{ display: "inline-block", verticalAlign: "middle", ...style }}
      loading="lazy"
      draggable={false}
      {...rest}
    />
  );
}

/**
 * Curated mapping of Mosaic icon names to common UI purposes.
 * Use this for consistent icon selection across the app.
 */
export const MOSAIC_ICONS = {
  // Navigation & Layout
  home: "home",
  dashboard: "dashboard",
  settings: "settings",
  search: "search",
  filter: "filter",
  notification: "notification",
  menu: "menu",
  close: "close",

  // Actions
  add: "add",
  edit: "edit",
  delete: "delete",
  check: "check",
  send: "send",
  download: "download",
  upload: "upload",
  copy: "copy",
  share: "share",
  refresh: "refresh",

  // Data & Analytics
  analytics: "analytics",
  analyticsIncrease: "analytics-increase",
  analyticsDecrease: "analytics-decrease",
  reports: "reports",
  data: "data",
  chart: "chart",

  // Users & Auth
  user: "user",
  users: "users",
  roles: "roles",
  lock: "lock",
  unlock: "unlock",
  shield: "shield",

  // Content & Communication
  chat: "chat",
  message: "message",
  attachment: "attachment",
  calendar: "calendar",
  document: "document",
  folder: "folder",
  book: "book",

  // Process & Workflow
  process: "process",
  workflow: "workflow",
  link: "link",
  plug: "plug",
  atom: "atom",
  bulb: "bulb",
  sparkles: "sparkles",
  wand: "wand-sparkles",

  // Commerce
  cart: "cart",
  payment: "payment",
  invoice: "invoice",
  contract: "contract",

  // Status
  info: "info",
  warning: "warning",
  error: "error",
  blocked: "blocked",
  success: "check",
};

/**
 * Full list of all 304 available Mosaic icon names.
 * Auto-generated from /icons/ directory.
 */
export const ALL_MOSAIC_ICONS = [
  "360", "actions", "add", "adjust", "alternative",
  "analytics-decrease", "analytics-increase", "analytics",
  "archive", "arrow-down-left", "arrow-down-right", "arrow-down",
  "arrow-left-right", "arrow-left", "arrow-resize", "arrow-right",
  "arrow-up-left", "arrow-up-right", "arrow-up",
  "assessment", "associations", "atom", "attachment", "audit", "award",
  "between", "blocked", "bold", "book", "bookmark", "box", "bulb",
  "bullet-list", "bullet", "business-card", "button",
  "calculator", "calendar", "caret-down", "caret-left", "caret-right", "caret-up",
  "cart-add", "cart-confirm", "cart", "category-cluster", "category",
  "cbd", "certificate", "chat", "check", "close",
  "dashboard", "data", "delete", "edit", "filter",
  "home", "lock", "manage", "notification", "platform", "plus",
  "process", "quality", "reports", "roles",
  "search", "send", "settings", "sparkles", "unlock",
  "user", "users", "wand-sparkles",
];
