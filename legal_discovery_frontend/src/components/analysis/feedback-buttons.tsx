'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle, XCircle, Edit3 } from 'lucide-react'

interface FeedbackButtonsProps {
  onFeedback: (feedback: string, approved: boolean) => Promise<void>
  categories: Array<{
    name: string
    description: string
    requires_document_search: boolean
  }>
}

export function FeedbackButtons({ onFeedback, categories }: FeedbackButtonsProps) {
  const [feedbackMode, setFeedbackMode] = useState<'buttons' | 'text'>('buttons')
  const [feedbackText, setFeedbackText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleApprove = async () => {
    setIsSubmitting(true)
    try {
      await onFeedback('Plan approved', true)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleModify = () => {
    setFeedbackMode('text')
  }

  const handleSubmitFeedback = async () => {
    if (!feedbackText.trim()) return
    
    setIsSubmitting(true)
    try {
      await onFeedback(feedbackText, false)
      setFeedbackText('')
      setFeedbackMode('buttons')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (feedbackMode === 'text') {
    return (
      <Card className="mt-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Provide Feedback</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            placeholder="Describe what changes you'd like to see in the analysis plan..."
            rows={4}
            className="resize-none"
          />
          
          <div className="flex space-x-2">
            <Button
              onClick={handleSubmitFeedback}
              disabled={!feedbackText.trim() || isSubmitting}
              size="sm"
            >
              Submit Feedback
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setFeedbackMode('buttons')
                setFeedbackText('')
              }}
              size="sm"
            >
              Cancel
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="mt-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Review Analysis Plan</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Categories Preview */}
        <div className="space-y-2">
          <p className="text-xs text-gray-600 font-medium">Proposed Categories:</p>
          <div className="space-y-2">
            {categories.map((category, index) => (
              <div key={index} className="flex items-start space-x-2 text-xs">
                <Badge 
                  variant={category.requires_document_search ? 'default' : 'secondary'}
                  className="text-xs"
                >
                  {category.requires_document_search ? 'Research' : 'Synthesis'}
                </Badge>
                <div className="flex-1">
                  <p className="font-medium">{category.name}</p>
                  <p className="text-gray-600">{category.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-2 pt-2">
          <Button
            onClick={handleApprove}
            disabled={isSubmitting}
            size="sm"
            className="feedback-button approve"
          >
            <CheckCircle className="h-4 w-4 mr-1" />
            Approve Plan
          </Button>
          
          <Button
            variant="outline"
            onClick={handleModify}
            disabled={isSubmitting}
            size="sm"
            className="feedback-button modify"
          >
            <Edit3 className="h-4 w-4 mr-1" />
            Modify Plan
          </Button>
        </div>

        <p className="text-xs text-gray-500">
          Approve to start analysis with this plan, or modify to provide specific feedback.
        </p>
      </CardContent>
    </Card>
  )
}