import "@testing-library/jest-dom";
import React from "react";
import { render, screen } from "@testing-library/react";
import Card, { CardHeader, CardBody, CardFooter } from "../../components/ui/Card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("applies hover effect class", () => {
    const { container } = render(<Card hover>Hoverable</Card>);
    expect(container.firstChild.className).toContain("hover:");
  });

  it("applies custom className", () => {
    const { container } = render(<Card className="mt-4">Styled</Card>);
    expect(container.firstChild.className).toContain("mt-4");
  });
});

describe("CardHeader", () => {
  it("renders children", () => {
    render(<CardHeader>Header</CardHeader>);
    expect(screen.getByText("Header")).toBeInTheDocument();
  });
});

describe("CardBody", () => {
  it("renders children", () => {
    render(<CardBody>Body</CardBody>);
    expect(screen.getByText("Body")).toBeInTheDocument();
  });
});

describe("CardFooter", () => {
  it("renders children", () => {
    render(<CardFooter>Footer</CardFooter>);
    expect(screen.getByText("Footer")).toBeInTheDocument();
  });
});

describe("Card composition", () => {
  it("renders full card with header, body, footer", () => {
    render(
      <Card>
        <CardHeader>Title</CardHeader>
        <CardBody>Content here</CardBody>
        <CardFooter>Actions</CardFooter>
      </Card>
    );
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("Content here")).toBeInTheDocument();
    expect(screen.getByText("Actions")).toBeInTheDocument();
  });
});
