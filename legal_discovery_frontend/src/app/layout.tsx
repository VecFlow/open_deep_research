import type { Metadata } from "next"
import "./globals.css"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Providers } from "./providers"

export const metadata: Metadata = {
  title: "Legal Discovery Agent",
  description: "AI-powered legal discovery and deposition preparation tool",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
} 