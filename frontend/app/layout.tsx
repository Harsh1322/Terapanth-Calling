import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sangam — Committee Contact Tracker",
  description: "A thoughtful workspace for committee outreach and follow-ups.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
