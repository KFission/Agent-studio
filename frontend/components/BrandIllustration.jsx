"use client";
/**
 * BrandIllustration — Renders a JAGGAER Mosaic branded illustration.
 * Illustrations are served as static files from /illustrations/{name}.svg
 *
 * Usage:
 *   <BrandIllustration name="empty" size={120} />
 *   <BrandIllustration name="error" size={80} className="opacity-80" />
 *
 * Available illustrations (24):
 *   analytics, decline, drop, empty, error, folder-closed, folder-open,
 *   incomplete, locked, message, process, search, selected, start,
 *   success, time, unselected, upload,
 *   accent-none, accent-zebra, borders-all, borders-bottom,
 *   density-compact, density-spacious
 */

export default function BrandIllustration({
  name,
  size = 120,
  width,
  height,
  className = "",
  style = {},
  title,
  ...rest
}) {
  if (!name) return null;
  const src = `/illustrations/${name}.svg`;
  const w = width || size;
  const h = height || size;
  return (
    <img
      src={src}
      alt={title || name}
      width={w}
      height={h}
      className={className}
      style={{ display: "block", margin: "0 auto", ...style }}
      loading="lazy"
      draggable={false}
      {...rest}
    />
  );
}

/**
 * Mapping of semantic use cases to illustration names.
 * Use this for consistent illustration selection across the app.
 */
export const ILLUSTRATIONS = {
  empty: "empty",
  error: "error",
  search: "search",
  success: "success",
  locked: "locked",
  upload: "upload",
  analytics: "analytics",
  start: "start",
  process: "process",
  message: "message",
  time: "time",
  decline: "decline",
  incomplete: "incomplete",
  selected: "selected",
  unselected: "unselected",
  folderClosed: "folder-closed",
  folderOpen: "folder-open",
  drop: "drop",
};
