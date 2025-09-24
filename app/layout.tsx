// app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";


export const metadata: Metadata = {
    title: "CodeRabbit Bait",
    description: "A deliberately imperfect Next.js app for review demos",
};


export default function RootLayout({ children }: { children: React.ReactNode }) {
    // NOTE: Missing lang attribute and other a11y attributes intentionally
    return (
        <html>
            <body>
                <header style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                    <h1>CodeRabbit Bait</h1>
                    <p>Intentionally messy in places to trigger review comments.</p>
                </header>
                <main style={{ padding: 12 }}>{children}</main>
            </body>
        </html>
    );
}