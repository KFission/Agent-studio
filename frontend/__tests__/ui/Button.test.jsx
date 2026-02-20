import "@testing-library/jest-dom";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import Button from "../../components/ui/Button";

describe("Button", () => {
  it("renders children text", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("fires onClick handler", () => {
    const onClick = jest.fn();
    render(<Button onClick={onClick}>Click</Button>);
    fireEvent.click(screen.getByText("Click"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled when disabled prop is true", () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByText("Disabled").closest("button")).toBeDisabled();
  });

  it("does not fire onClick when disabled", () => {
    const onClick = jest.fn();
    render(<Button disabled onClick={onClick}>No</Button>);
    fireEvent.click(screen.getByText("No"));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("renders with primary variant by default", () => {
    const { container } = render(<Button>Primary</Button>);
    const btn = container.querySelector("button");
    expect(btn.className).toContain("bg-jai-primary");
  });

  it("renders secondary variant with border", () => {
    const { container } = render(<Button variant="secondary">Secondary</Button>);
    const btn = container.querySelector("button");
    expect(btn.className).toContain("border");
  });

  it("renders ghost variant", () => {
    const { container } = render(<Button variant="ghost">Ghost</Button>);
    const btn = container.querySelector("button");
    expect(btn.className).not.toContain("bg-jai-primary");
  });

  it("renders sm size", () => {
    const { container } = render(<Button size="sm">Small</Button>);
    const btn = container.querySelector("button");
    expect(btn.className).toContain("text-xs");
  });

  it("renders lg size", () => {
    const { container } = render(<Button size="lg">Large</Button>);
    const btn = container.querySelector("button");
    expect(btn.className).toContain("rounded-xl");
  });

  it("shows loading spinner when loading", () => {
    const { container } = render(<Button loading>Loading</Button>);
    const btn = container.querySelector("button");
    expect(btn.className).toContain("opacity-50");
    expect(btn).toBeDisabled();
  });

  it("applies custom className", () => {
    const { container } = render(<Button className="ml-4">Custom</Button>);
    const btn = container.querySelector("button");
    expect(btn.className).toContain("ml-4");
  });
});
