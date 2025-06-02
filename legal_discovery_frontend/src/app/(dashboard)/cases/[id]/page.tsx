import { Suspense } from 'react'
import { notFound } from 'next/navigation'
import { CaseDetails } from '@/components/cases/case-details'
import { ChatInterface } from '@/components/analysis/chat-interface'
import { AnalysisDashboard } from '@/components/analysis/analysis-dashboard'
import { CaseDetailsLoading } from '@/components/cases/case-details-loading'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface CasePageProps {
  params: Promise<{ id: string }>
  searchParams: Promise<{ tab?: string }>
}

export default async function CasePage({ params, searchParams }: CasePageProps) {
  const { id } = await params
  const { tab = 'chat' } = await searchParams
  
  if (!id) {
    notFound()
  }

  return (
    <div className="h-full">
      <div className="px-4 sm:px-6 lg:px-8 py-8">
        <Suspense fallback={<CaseDetailsLoading />}>
          <CaseDetails caseId={id} />
        </Suspense>
        
        <div className="mt-8">
          <Tabs defaultValue={tab} className="h-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="chat">Chat Analysis</TabsTrigger>
              <TabsTrigger value="dashboard">Progress Dashboard</TabsTrigger>
              <TabsTrigger value="documents">Documents</TabsTrigger>
            </TabsList>
            
            <TabsContent value="chat" className="mt-6">
              <div className="h-[calc(100vh-12rem)]">
                <Suspense fallback={<div>Loading chat...</div>}>
                  <ChatInterface caseId={id} />
                </Suspense>
              </div>
            </TabsContent>
            
            <TabsContent value="dashboard" className="mt-6">
              <div className="h-[calc(100vh-12rem)]">
                <Suspense fallback={<div>Loading dashboard...</div>}>
                  <AnalysisDashboard caseId={id} />
                </Suspense>
              </div>
            </TabsContent>
            
            <TabsContent value="documents" className="mt-6">
              <div className="h-[calc(100vh-12rem)]">
                <div className="text-center py-12">
                  <h3 className="text-lg font-medium text-gray-900">Document Viewer</h3>
                  <p className="mt-2 text-sm text-gray-500">
                    Document integration coming soon
                  </p>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}