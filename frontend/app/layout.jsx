import "./globals.css";

export const metadata = {
  title: "JAI Agent OS",
  description: "JAGGAER AI Agent Operating System — Low-Code/No-Code Agent Builder",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
