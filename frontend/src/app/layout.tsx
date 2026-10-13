import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Content-Origin Detective",
  description: "Production Digital Forensics, Multi-Signal Neural Ensemble, and Secure Custody Verification.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-cyan-500 selection:text-black">
        {children}
      </body>
    </html>
  );
}
