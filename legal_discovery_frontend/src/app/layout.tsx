import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from '@/components/providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Legal Discovery Assistant',
  description: 'AI-powered legal analysis and discovery platform for litigation preparation',
  keywords: ['legal', 'discovery', 'analysis', 'litigation', 'AI', 'assistant'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} h-full antialiased`}>
        <Providers>
          <div className="min-h-full bg-background">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  )
}