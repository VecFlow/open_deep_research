'use client'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { CheckCircle, Clock, FileText, Search } from 'lucide-react'

interface CategoryProgressProps {
  categories: Array<{
    name: string
    description: string
    requires_document_search: boolean
    content?: string
  }>
  progress: Array<{
    id: string
    category_name: string
    status: string
    content?: string
    search_iterations: number
    started_at?: string
    completed_at?: string
  }>
}

export function CategoryProgress({ categories, progress }: CategoryProgressProps) {
  const getProgressForCategory = (categoryName: string) => {
    return progress.find(p => p.category_name === categoryName)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'in_progress':
        return <Clock className="h-4 w-4 text-blue-600 animate-pulse" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    return (
      <Badge 
        variant={status === 'completed' ? 'default' : 'secondary'}
        className={`text-xs ${
          status === 'completed' ? 'status-completed' :
          status === 'in_progress' ? 'status-in-progress' :
          'status-pending'
        }`}
      >
        {status?.replace('_', ' ') || 'pending'}
      </Badge>
    )
  }

  const completedCount = progress.filter(p => p.status === 'completed').length
  const totalCount = categories.length
  const progressPercentage = totalCount > 0 ? (completedCount / totalCount) * 100 : 0

  return (
    <div className="space-y-4">
      {/* Overall Progress */}
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">Categories Progress</span>
        <span>{completedCount}/{totalCount} Complete</span>
      </div>
      <Progress value={progressPercentage} className="w-full" />

      {/* Individual Categories */}
      <div className="space-y-3">
        {categories.map((category, index) => {
          const categoryProgress = getProgressForCategory(category.name)
          const status = categoryProgress?.status || 'pending'

          return (
            <Card key={index} className="border border-gray-200">
              <CardContent className="p-4">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-0.5">
                    {getStatusIcon(status)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-medium text-gray-900">
                        {category.name}
                      </h4>
                      <div className="flex items-center space-x-2 ml-2">
                        {category.requires_document_search && (
                          <Badge variant="outline" className="text-xs">
                            <Search className="h-3 w-3 mr-1" />
                            Research
                          </Badge>
                        )}
                        {getStatusBadge(status)}
                      </div>
                    </div>
                    
                    <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                      {category.description}
                    </p>
                    
                    {categoryProgress && (
                      <div className="mt-2 space-y-1">
                        {categoryProgress.search_iterations > 0 && (
                          <div className="flex items-center text-xs text-gray-500">
                            <FileText className="h-3 w-3 mr-1" />
                            {categoryProgress.search_iterations} search iteration{categoryProgress.search_iterations !== 1 ? 's' : ''}
                          </div>
                        )}
                        
                        {categoryProgress.content && status === 'completed' && (
                          <div className="text-xs text-gray-600 bg-gray-50 rounded p-2 mt-2">
                            <p className="line-clamp-3">
                              {categoryProgress.content.slice(0, 200)}...
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}