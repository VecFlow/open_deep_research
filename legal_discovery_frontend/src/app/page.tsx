import { LegalDiscoveryInterface } from "@/components/legal-discovery/legal-discovery-interface"

export default function HomePage() {
  return (
    <main className="min-h-screen bg-white">
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Simple header similar to Manus */}
        <div className="flex items-center gap-3 mb-8">
          <h1 className="text-xl font-medium text-gray-900">Oliver Deposition Workflow</h1>
        </div>
        
        <LegalDiscoveryInterface />
      </div>
    </main>
  )
} 