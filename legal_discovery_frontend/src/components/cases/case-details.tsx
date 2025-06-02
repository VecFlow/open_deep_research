'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useCaseAnalysis } from '@/lib/cases/queries'
import { formatRelativeTime } from '@/lib/utils'
import { Calendar, FileText, Clock } from 'lucide-react'

interface CaseDetailsProps {
  caseId: string
}

export function CaseDetails({ caseId }: CaseDetailsProps) {
  const { data: caseData, isLoading, error } = useCaseAnalysis(caseId)

  if (isLoading) {
    return <CaseDetailsLoading />
  }

  if (error || !caseData) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Error loading case details</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Case Header */}
      <div className="border-b border-gray-200 pb-5">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">
              {caseData.title}
            </h1>
            <div className="mt-1 flex flex-col sm:mt-0 sm:flex-row sm:flex-wrap sm:space-x-6">
              <div className="mt-2 flex items-center text-sm text-gray-500">
                <Calendar className="mr-1.5 h-4 w-4 flex-shrink-0 text-gray-400" />
                Created {formatRelativeTime(caseData.created_at)}
              </div>
              <div className="mt-2 flex items-center text-sm text-gray-500">
                <Clock className="mr-1.5 h-4 w-4 flex-shrink-0 text-gray-400" />
                Updated {formatRelativeTime(caseData.updated_at)}
              </div>
              <div className="mt-2 flex items-center text-sm text-gray-500">
                <FileText className="mr-1.5 h-4 w-4 flex-shrink-0 text-gray-400" />
                {caseData.analyses.length} analysis
              </div>
            </div>
          </div>
          <div className="ml-6 flex-shrink-0">
            <Badge 
              variant={caseData.status === 'completed' ? 'default' : 'secondary'}
              className={`
                ${caseData.status === 'completed' ? 'status-completed' :
                  caseData.status === 'in_progress' ? 'status-in-progress' :
                  caseData.status === 'paused' ? 'status-paused' :
                  'status-pending'}
              `}
            >
              {caseData.status.replace('_', ' ')}
            </Badge>
          </div>
        </div>
      </div>

      {/* Case Background */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Case Background</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-700 leading-relaxed">
            {caseData.background}
          </p>
        </CardContent>
      </Card>

      {/* Analysis Summary */}
      {caseData.analyses.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Analysis Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {caseData.analyses.map((analysis) => (
                <div key={analysis.id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      Analysis #{analysis.id.slice(0, 8)}
                    </p>
                    <p className="text-xs text-gray-500">
                      {analysis.current_step && `Step: ${analysis.current_step}`}
                    </p>
                  </div>
                  <Badge variant="outline" className={`
                    ${analysis.status === 'completed' ? 'status-completed' :
                      analysis.status === 'in_progress' ? 'status-in-progress' :
                      analysis.status === 'paused' ? 'status-paused' :
                      'status-pending'}
                  `}>
                    {analysis.status.replace('_', ' ')}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function CaseDetailsLoading() {
  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-5">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/3"></div>
          </div>
        </div>
      </div>
      
      <div className="legal-card animate-pulse">
        <div className="p-6">
          <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded w-full"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    </div>
  )
}