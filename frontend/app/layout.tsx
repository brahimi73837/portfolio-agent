import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Brahim — AI Portfolio",
  description: "Chat with Brahim's AI assistant about his work, projects, and skills.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
