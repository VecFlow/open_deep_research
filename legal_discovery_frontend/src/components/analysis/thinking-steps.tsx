'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { ChevronDown, ChevronRight, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ThinkingStep {
  id: string
  title: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  description?: string
  details?: string
  timestamp?: Date
  substeps?: ThinkingStep[]
}

interface ThinkingStepsProps {
  categories: Array<{
    name: string
    description: string
    content?: string
    status?: string
  }>
  currentStep: string
}

export function ThinkingSteps({ categories, currentStep }: ThinkingStepsProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())

  const toggleStep = (stepId: string) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId)
    } else {
      newExpanded.add(stepId)
    }
    setExpandedSteps(newExpanded)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'in_progress':
        return <Clock className="h-4 w-4 text-blue-600 animate-pulse" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-600" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      pending: 'secondary',
      in_progress: 'default',
      completed: 'default',
      failed: 'destructive'
    }
    
    return (
      <Badge 
        variant={variants[status] || 'secondary'}
        className={cn(
          'text-xs',
          status === 'completed' && 'bg-green-100 text-green-700 border-green-300',
          status === 'in_progress' && 'bg-blue-100 text-blue-700 border-blue-300'
        )}
      >
        {status.replace('_', ' ')}
      </Badge>
    )
  }

  // Convert categories to thinking steps
  const steps: ThinkingStep[] = categories.map((category, index) => ({
    id: `category_${index}`,
    title: category.name,
    status: category.status as any || 'pending',
    description: category.description,
    details: category.content,
    timestamp: new Date()
  }))

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900">Analysis Progress</h3>
        <Badge variant="outline" className="text-xs">
          {steps.filter(s => s.status === 'completed').length} / {steps.length} Complete
        </Badge>
      </div>

      <div className="space-y-2">
        {steps.map((step, index) => {
          const isExpanded = expandedSteps.has(step.id)
          const hasDetails = Boolean(step.details || step.substeps?.length)

          return (
            <Card key={step.id} className={cn(
              'thinking-step',
              step.status === 'in_progress' && 'active',
              step.status === 'completed' && 'completed'
            )}>
              <CardContent className="p-3">
                <Collapsible>
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 mt-0.5">
                      {getStatusIcon(step.status)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-900">
                            {step.title}
                          </p>
                          {step.description && (
                            <p className="text-xs text-gray-600 mt-1">
                              {step.description}
                            </p>
                          )}
                        </div>
                        
                        <div className="flex items-center space-x-2 ml-2">
                          {getStatusBadge(step.status)}
                          {hasDetails && (
                            <CollapsibleTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => toggleStep(step.id)}
                                className="p-1 h-6 w-6"
                              >
                                {isExpanded ? (
                                  <ChevronDown className="h-3 w-3" />
                                ) : (
                                  <ChevronRight className="h-3 w-3" />
                                )}
                              </Button>
                            </CollapsibleTrigger>
                          )}
                        </div>
                      </div>
                      
                      {step.status === 'in_progress' && (
                        <div className="mt-2">
                          <div className="flex items-center space-x-2">
                            <div className="flex-1 bg-gray-200 rounded-full h-1">
                              <div className="bg-blue-600 h-1 rounded-full animate-thinking w-full"></div>
                            </div>
                            <span className="text-xs text-gray-500">Processing...</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {hasDetails && (
                    <CollapsibleContent className="mt-3 pl-7">
                      {step.details && (
                        <div className="text-xs text-gray-600 bg-gray-50 rounded p-2">
                          <div className="document-content">
                            {step.details.split('\n').map((line, i) => (
                              <p key={i}>{line}</p>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {step.substeps && (
                        <div className="space-y-2 mt-2">
                          {step.substeps.map((substep) => (
                            <div key={substep.id} className="flex items-center space-x-2 text-xs">
                              {getStatusIcon(substep.status)}
                              <span className="text-gray-700">{substep.title}</span>
                              {getStatusBadge(substep.status)}
                            </div>
                          ))}
                        </div>
                      )}
                    </CollapsibleContent>
                  )}
                </Collapsible>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Overall Progress */}
      <div className="pt-2 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>Overall Progress</span>
          <span>
            {Math.round((steps.filter(s => s.status === 'completed').length / steps.length) * 100)}%
          </span>
        </div>
        <div className="progress-bar mt-1">
          <div 
            className="progress-fill"
            style={{ 
              width: `${(steps.filter(s => s.status === 'completed').length / steps.length) * 100}%` 
            }}
          />
        </div>
      </div>
    </div>
  )
}