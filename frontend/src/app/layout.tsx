import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "F1 తెలుగు కామెంటరీ | Telugu Live Commentary",
  description:
    "Real-time Telugu commentary for Formula 1 races with live leaderboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="te">
      <body>{children}</body>
    </html>
  );
}
