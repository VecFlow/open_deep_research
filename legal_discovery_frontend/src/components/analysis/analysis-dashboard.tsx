'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { useCaseAnalysis } from '@/lib/cases/queries'
import { useAnalysisWorkflow } from '@/lib/analysis/queries'
import { CategoryProgress } from './category-progress'
import { ThinkingSteps } from './thinking-steps'

interface AnalysisDashboardProps {
  caseId: string
}

export function AnalysisDashboard({ caseId }: AnalysisDashboardProps) {
  const { data: caseData } = useCaseAnalysis(caseId)
  const { data: workflowStatus } = useAnalysisWorkflow(caseId)

  const latestAnalysis = caseData?.analyses?.[0]

  return (
    <div className="space-y-6">
      {/* Overall Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Analysis Progress</span>
            {workflowStatus && (
              <Badge 
                variant={workflowStatus.status === 'completed' ? 'default' : 'secondary'}
                className={`
                  ${workflowStatus.status === 'completed' ? 'status-completed' :
                    workflowStatus.status === 'in_progress' ? 'status-in-progress' :
                    workflowStatus.status === 'paused' ? 'status-paused' :
                    'status-pending'}
                `}
              >
                {workflowStatus.status.replace('_', ' ')}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {workflowStatus && (
            <>
              <div className="flex items-center justify-between text-sm">
                <span>Overall Progress</span>
                <span>{Math.round(workflowStatus.progress_percentage)}%</span>
              </div>
              <Progress value={workflowStatus.progress_percentage} className="w-full" />
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>
                  {workflowStatus.categories_completed} of {workflowStatus.total_categories} categories completed
                </span>
                {workflowStatus.current_step && (
                  <span>Current: {workflowStatus.current_step}</span>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Category Breakdown */}
      {latestAnalysis && (
        <Card>
          <CardHeader>
            <CardTitle>Category Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <CategoryProgress 
              categories={latestAnalysis.categories || []}
              progress={latestAnalysis.category_progress || []}
            />
          </CardContent>
        </Card>
      )}

      {/* Thinking Steps */}
      {latestAnalysis?.categories && (
        <Card>
          <CardHeader>
            <CardTitle>Analysis Steps</CardTitle>
          </CardHeader>
          <CardContent>
            <ThinkingSteps
              categories={latestAnalysis.categories}
              currentStep={latestAnalysis.current_step || 'planning'}
            />
          </CardContent>
        </Card>
      )}

      {/* Feedback Status */}
      {workflowStatus?.feedback_requested && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader>
            <CardTitle className="text-orange-800">Feedback Required</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-orange-700">
              {workflowStatus.feedback_message || 'Human input is required to continue the analysis.'}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}