import { Suspense } from 'react'
import { CasesList } from '@/components/cases/cases-list'
import { CreateCaseButton } from '@/components/cases/create-case-button'
import { CasesHeader } from '@/components/cases/cases-header'
import { CasesLoading } from '@/components/cases/cases-loading'

interface CasesPageProps {
  searchParams: Promise<{
    status?: string
    page?: string
  }>
}

export default async function CasesPage({ searchParams }: CasesPageProps) {
  const params = await searchParams
  
  return (
    <div className="h-full">
      <div className="px-4 sm:px-6 lg:px-8 py-8">
        <CasesHeader />
        
        <div className="mt-8">
          <div className="sm:flex sm:items-center">
            <div className="sm:flex-auto">
              <h1 className="text-2xl font-semibold text-gray-900">Legal Cases</h1>
              <p className="mt-2 text-sm text-gray-700">
                Manage your legal cases and track analysis progress
              </p>
            </div>
            <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
              <CreateCaseButton />
            </div>
          </div>
          
          <div className="mt-8">
            <Suspense fallback={<CasesLoading />}>
              <CasesList 
                status={params.status}
                page={params.page ? parseInt(params.page) : 1}
              />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  )
}