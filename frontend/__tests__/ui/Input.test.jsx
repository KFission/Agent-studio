import "@testing-library/jest-dom";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import Input from "../../components/ui/Input";

describe("Input", () => {
  it("renders with placeholder", () => {
    render(<Input placeholder="Enter name" />);
    expect(screen.getByPlaceholderText("Enter name")).toBeInTheDocument();
  });

  it("renders label when provided", () => {
    render(<Input label="Email" />);
    expect(screen.getByText("Email")).toBeInTheDocument();
  });

  it("renders hint text", () => {
    render(<Input hint="Must be unique" />);
    expect(screen.getByText("Must be unique")).toBeInTheDocument();
  });

  it("renders error state", () => {
    render(<Input error="Required field" />);
    expect(screen.getByText("Required field")).toBeInTheDocument();
  });

  it("calls onChange when typing", () => {
    const onChange = jest.fn();
    render(<Input onChange={onChange} placeholder="Type" />);
    fireEvent.change(screen.getByPlaceholderText("Type"), { target: { value: "hello" } });
    expect(onChange).toHaveBeenCalled();
  });

  it("is disabled when disabled prop set", () => {
    render(<Input disabled placeholder="Disabled" />);
    expect(screen.getByPlaceholderText("Disabled")).toBeDisabled();
  });
});
