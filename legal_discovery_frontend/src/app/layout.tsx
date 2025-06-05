import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Providers } from "./providers"

const inter = Inter({ subsets: ["latin"] })

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
      <body className={inter.className}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
} 