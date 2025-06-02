'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useCases } from '@/lib/cases/queries'
import { formatRelativeTime, getStatusColor } from '@/lib/utils'
import { FileText, Clock, CheckCircle } from 'lucide-react'
import Link from 'next/link'

interface CasesListProps {
  status?: string
  page?: number
}

export function CasesList({ status, page = 1 }: CasesListProps) {
  const { data: cases, isLoading, error } = useCases({ status, page })

  if (isLoading) {
    return <div>Loading cases...</div>
  }

  if (error) {
    return <div>Error loading cases: {error.message}</div>
  }

  if (!cases || cases.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">No cases</h3>
        <p className="mt-1 text-sm text-gray-500">
          Get started by creating a new legal case.
        </p>
      </div>
    )
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {cases.map((case_) => (
        <Card key={case_.id} className="legal-card">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between">
              <CardTitle className="text-lg font-medium line-clamp-2">
                {case_.title}
              </CardTitle>
              <Badge 
                variant={case_.status === 'completed' ? 'default' : 'secondary'}
                className={`ml-2 ${
                  case_.status === 'completed' ? 'status-completed' :
                  case_.status === 'in_progress' ? 'status-in-progress' :
                  case_.status === 'paused' ? 'status-paused' :
                  'status-pending'
                }`}
              >
                {case_.status.replace('_', ' ')}
              </Badge>
            </div>
          </CardHeader>
          
          <CardContent className="pt-0">
            <p className="text-sm text-gray-600 line-clamp-3 mb-4">
              {case_.background}
            </p>
            
            <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
              <div className="flex items-center">
                <Clock className="h-4 w-4 mr-1" />
                {case_.updated_at ? formatRelativeTime(case_.updated_at) : 'Recently created'}
              </div>
              
              {case_.analyses.length > 0 && (
                <div className="flex items-center">
                  <CheckCircle className="h-4 w-4 mr-1" />
                  {case_.analyses.length} analysis
                </div>
              )}
            </div>
            
            <Link href={`/cases/${case_.id}`}>
              <Button className="w-full" size="sm">
                View Case
              </Button>
            </Link>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}