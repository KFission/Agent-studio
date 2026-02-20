"use client";
import "@testing-library/jest-dom";
import React from "react";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import {
  Badge, BADGE_VARIANTS, SearchInput, EmptyState, Skeleton, Tabs, StatCard,
  toast, toastStore, ToastContainer, confirmAction, ConfirmDialog,
  relativeTime, ApiSnippetModal, Breadcrumbs,
} from "../../components/shared/StudioUI";

// ═══════════════════════════════════════════════════════════════════
// BADGE
// ═══════════════════════════════════════════════════════════════════

describe("Badge", () => {
  it("renders children text", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies default outline variant", () => {
    const { container } = render(<Badge>Test</Badge>);
    const el = container.firstChild;
    expect(el.className).toContain("border");
    expect(el.className).toContain("text-slate-500");
  });

  it("applies brand variant", () => {
    const { container } = render(<Badge variant="brand">Brand</Badge>);
    const el = container.firstChild;
    expect(el.className).toContain("text-jai-primary");
  });

  it("applies success variant", () => {
    const { container } = render(<Badge variant="success">OK</Badge>);
    const el = container.firstChild;
    expect(el.className).toContain("text-emerald-600");
  });

  it("applies danger variant", () => {
    const { container } = render(<Badge variant="danger">Error</Badge>);
    const el = container.firstChild;
    expect(el.className).toContain("text-red-600");
  });

  it("applies custom className", () => {
    const { container } = render(<Badge className="ml-2">Custom</Badge>);
    expect(container.firstChild.className).toContain("ml-2");
  });

  it("renders all defined variants without error", () => {
    Object.keys(BADGE_VARIANTS).forEach((variant) => {
      const { unmount } = render(<Badge variant={variant}>{variant}</Badge>);
      expect(screen.getByText(variant)).toBeInTheDocument();
      unmount();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════
// SEARCH INPUT
// ═══════════════════════════════════════════════════════════════════

describe("SearchInput", () => {
  it("renders with placeholder", () => {
    render(<SearchInput value="" onChange={() => {}} placeholder="Search agents..." />);
    expect(screen.getByPlaceholderText("Search agents...")).toBeInTheDocument();
  });

  it("displays the current value", () => {
    render(<SearchInput value="hello" onChange={() => {}} />);
    expect(screen.getByDisplayValue("hello")).toBeInTheDocument();
  });

  it("calls onChange when typing", () => {
    const onChange = jest.fn();
    render(<SearchInput value="" onChange={onChange} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "test" } });
    expect(onChange).toHaveBeenCalledWith("test");
  });

  it("uses default placeholder when none provided", () => {
    render(<SearchInput value="" onChange={() => {}} />);
    expect(screen.getByPlaceholderText("Search...")).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════
// EMPTY STATE
// ═══════════════════════════════════════════════════════════════════

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(<EmptyState title="No agents" description="Create your first agent" />);
    expect(screen.getByText("No agents")).toBeInTheDocument();
    expect(screen.getByText("Create your first agent")).toBeInTheDocument();
  });

  it("renders action button when provided", () => {
    render(<EmptyState title="Empty" description="Nothing" action={<button>Create</button>} />);
    expect(screen.getByText("Create")).toBeInTheDocument();
  });

  it("renders icon when provided and no illustration", () => {
    render(<EmptyState icon={<span data-testid="icon">IC</span>} title="No data" description="d" />);
    expect(screen.getByTestId("icon")).toBeInTheDocument();
  });

  it("renders illustration image when provided", () => {
    const { container } = render(<EmptyState illustration="search" title="No results" description="d" />);
    const img = container.querySelector("img");
    expect(img).toBeInTheDocument();
    expect(img.getAttribute("src")).toContain("search");
  });
});

// ═══════════════════════════════════════════════════════════════════
// SKELETON
// ═══════════════════════════════════════════════════════════════════

describe("Skeleton", () => {
  it("renders with animate-pulse class", () => {
    const { container } = render(<Skeleton className="h-5 w-40" />);
    expect(container.firstChild.className).toContain("animate-pulse");
  });

  it("applies custom className", () => {
    const { container } = render(<Skeleton className="h-10 w-10 rounded-xl" />);
    expect(container.firstChild.className).toContain("h-10");
    expect(container.firstChild.className).toContain("rounded-xl");
  });
});

// ═══════════════════════════════════════════════════════════════════
// TABS
// ═══════════════════════════════════════════════════════════════════

describe("Tabs", () => {
  it("renders all tab labels", () => {
    render(<Tabs tabs={["Users", "Roles"]} active="Users" onChange={() => {}} />);
    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(screen.getByText("Roles")).toBeInTheDocument();
  });

  it("highlights the active tab", () => {
    render(<Tabs tabs={["A", "B"]} active="A" onChange={() => {}} />);
    const activeBtn = screen.getByText("A");
    expect(activeBtn.className).toContain("bg-white");
    expect(activeBtn.className).toContain("text-slate-900");
  });

  it("fires onChange when clicking inactive tab", () => {
    const onChange = jest.fn();
    render(<Tabs tabs={["A", "B"]} active="A" onChange={onChange} />);
    fireEvent.click(screen.getByText("B"));
    expect(onChange).toHaveBeenCalledWith("B");
  });
});

// ═══════════════════════════════════════════════════════════════════
// STAT CARD
// ═══════════════════════════════════════════════════════════════════

describe("StatCard", () => {
  it("renders label and value", () => {
    render(<StatCard label="Total Runs" value="1,234" />);
    expect(screen.getByText("Total Runs")).toBeInTheDocument();
    expect(screen.getByText("1,234")).toBeInTheDocument();
  });

  it("renders trend when provided", () => {
    render(<StatCard label="Cost" value="$50" trend="+12%" />);
    expect(screen.getByText("+12%")).toBeInTheDocument();
  });

  it("applies green color for positive trend", () => {
    render(<StatCard label="L" value="V" trend="+5%" />);
    const trendEl = screen.getByText("+5%");
    expect(trendEl.className).toContain("text-emerald-600");
  });

  it("applies red color for negative trend", () => {
    render(<StatCard label="L" value="V" trend="-3%" />);
    const trendEl = screen.getByText("-3%");
    expect(trendEl.className).toContain("text-red-500");
  });
});

// ═══════════════════════════════════════════════════════════════════
// TOAST SYSTEM
// ═══════════════════════════════════════════════════════════════════

describe("Toast system", () => {
  beforeEach(() => {
    toastStore.toasts = [];
  });

  it("toast() adds a toast to the store", () => {
    toast("Hello");
    expect(toastStore.toasts.length).toBe(1);
    expect(toastStore.toasts[0].message).toBe("Hello");
    expect(toastStore.toasts[0].type).toBe("success");
  });

  it("toast.error() creates an error toast", () => {
    toast.error("Fail");
    expect(toastStore.toasts[toastStore.toasts.length - 1].type).toBe("error");
  });

  it("toast.info() creates an info toast", () => {
    toast.info("Info");
    expect(toastStore.toasts[toastStore.toasts.length - 1].type).toBe("info");
  });

  it("toast.warning() creates a warning toast", () => {
    toast.warning("Warn");
    expect(toastStore.toasts[toastStore.toasts.length - 1].type).toBe("warning");
  });

  it("ToastContainer renders toasts", () => {
    const { rerender } = render(<ToastContainer />);
    act(() => { toast.success("Visible toast"); });
    rerender(<ToastContainer />);
    expect(screen.getByText("Visible toast")).toBeInTheDocument();
  });

  it("ToastContainer dismiss button removes toast", () => {
    const { rerender, container } = render(<ToastContainer />);
    let id;
    act(() => { id = toast.success("Dismissable"); });
    rerender(<ToastContainer />);
    expect(screen.getByText("Dismissable")).toBeInTheDocument();
    const dismissBtn = container.querySelector("button");
    act(() => { fireEvent.click(dismissBtn); });
    expect(toastStore.toasts.find(t => t.id === id)).toBeUndefined();
  });
});

// ═══════════════════════════════════════════════════════════════════
// CONFIRM DIALOG
// ═══════════════════════════════════════════════════════════════════

describe("ConfirmDialog", () => {
  it("renders when confirmAction is called", async () => {
    const { rerender } = render(<ConfirmDialog />);
    expect(screen.queryByText("Delete Agent")).toBeNull();
    act(() => {
      confirmAction({ title: "Delete Agent", message: "Are you sure?", confirmLabel: "Delete" });
    });
    rerender(<ConfirmDialog />);
    expect(screen.getByText("Delete Agent")).toBeInTheDocument();
    expect(screen.getByText("Are you sure?")).toBeInTheDocument();
  });

  it("resolves true when confirmed", async () => {
    const { rerender } = render(<ConfirmDialog />);
    let result;
    act(() => {
      confirmAction({ title: "Confirm?", message: "Do it?" }).then(r => { result = r; });
    });
    rerender(<ConfirmDialog />);
    act(() => { fireEvent.click(screen.getByText("Delete")); });
    rerender(<ConfirmDialog />);
    await waitFor(() => expect(result).toBe(true));
  });

  it("resolves false when cancelled", async () => {
    const { rerender } = render(<ConfirmDialog />);
    let result;
    act(() => {
      confirmAction({ title: "Cancel?", message: "Nope" }).then(r => { result = r; });
    });
    rerender(<ConfirmDialog />);
    act(() => { fireEvent.click(screen.getByText("Cancel")); });
    rerender(<ConfirmDialog />);
    await waitFor(() => expect(result).toBe(false));
  });
});

// ═══════════════════════════════════════════════════════════════════
// RELATIVE TIME
// ═══════════════════════════════════════════════════════════════════

describe("relativeTime", () => {
  it("returns empty string for falsy input", () => {
    expect(relativeTime(null)).toBe("");
    expect(relativeTime("")).toBe("");
    expect(relativeTime(undefined)).toBe("");
  });

  it("returns 'just now' for very recent timestamps", () => {
    expect(relativeTime(new Date().toISOString())).toBe("just now");
  });

  it("returns 'Xm ago' for timestamps within an hour", () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(relativeTime(fiveMinAgo)).toMatch(/5m ago/);
  });

  it("returns 'Xh ago' for timestamps within a day", () => {
    const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString();
    expect(relativeTime(threeHoursAgo)).toMatch(/3h ago/);
  });

  it("returns 'Xd ago' for timestamps within a week", () => {
    const twoDaysAgo = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString();
    expect(relativeTime(twoDaysAgo)).toMatch(/2d ago/);
  });

  it("returns 'just now' for future timestamps", () => {
    const future = new Date(Date.now() + 60000).toISOString();
    expect(relativeTime(future)).toBe("just now");
  });
});

// ═══════════════════════════════════════════════════════════════════
// BREADCRUMBS
// ═══════════════════════════════════════════════════════════════════

describe("Breadcrumbs", () => {
  it("returns null for single item", () => {
    const { container } = render(<Breadcrumbs items={[{ label: "Home" }]} />);
    expect(container.innerHTML).toBe("");
  });

  it("returns null for empty/no items", () => {
    const { container } = render(<Breadcrumbs items={[]} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders multiple breadcrumbs", () => {
    render(<Breadcrumbs items={[{ label: "Home", onClick: () => {} }, { label: "Agents" }]} />);
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Agents")).toBeInTheDocument();
  });

  it("fires onClick for clickable breadcrumb", () => {
    const onClick = jest.fn();
    render(<Breadcrumbs items={[{ label: "Home", onClick }, { label: "Agents" }]} />);
    fireEvent.click(screen.getByText("Home"));
    expect(onClick).toHaveBeenCalled();
  });
});
