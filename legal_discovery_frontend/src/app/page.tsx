import { LegalDiscoveryInterface } from "@/components/legal-discovery/legal-discovery-interface"

export default function HomePage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold tracking-tight mb-2">
            Legal Discovery Agent
          </h1>
          <p className="text-muted-foreground text-lg">
            AI-powered legal discovery and deposition preparation tool
          </p>
        </div>
        
        <LegalDiscoveryInterface />
      </div>
    </main>
  )
} 