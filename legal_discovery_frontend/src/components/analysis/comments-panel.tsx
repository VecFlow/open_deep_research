'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { formatRelativeTime } from '@/lib/utils'
import { MessageCircle, Plus } from 'lucide-react'

interface CommentsPanelProps {
  caseId: string
}

// Mock comments data - would come from API
const mockComments = [
  {
    id: '1',
    content: 'Need to focus more on the damages calculation section. The current analysis seems incomplete.',
    context_type: 'category',
    context_reference: 'Damages Assessment',
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
  },
  {
    id: '2', 
    content: 'Great analysis on the contract terms. This provides solid foundation for our argument.',
    context_type: 'category',
    context_reference: 'Contract Analysis',
    created_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(), // 5 hours ago
  },
  {
    id: '3',
    content: 'The deposition questions look comprehensive. Should we add questions about the timeline?',
    context_type: 'deposition',
    context_reference: 'Witness Questions',
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
  }
]

export function CommentsPanel({ caseId }: CommentsPanelProps) {
  const [newComment, setNewComment] = useState('')
  const [isAdding, setIsAdding] = useState(false)
  const [comments] = useState(mockComments) // Would use query hook in real app

  const handleAddComment = async () => {
    if (!newComment.trim()) return
    
    setIsAdding(true)
    try {
      // TODO: Implement API call to add comment
      console.log('Adding comment:', newComment)
      setNewComment('')
    } finally {
      setIsAdding(false)
    }
  }

  const getContextBadge = (contextType?: string) => {
    if (!contextType) return null
    
    const variants = {
      category: 'default',
      deposition: 'secondary',
      general: 'outline'
    } as const
    
    return (
      <Badge variant={variants[contextType as keyof typeof variants] || 'outline'} className="text-xs">
        {contextType}
      </Badge>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-gray-200 p-4">
        <h3 className="text-sm font-medium text-gray-900 flex items-center">
          <MessageCircle className="h-4 w-4 mr-2" />
          Comments & Notes
        </h3>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {comments.length === 0 ? (
            <div className="text-center py-8">
              <MessageCircle className="mx-auto h-8 w-8 text-gray-400" />
              <p className="mt-2 text-sm text-gray-500">No comments yet</p>
              <p className="text-xs text-gray-400">Add notes and feedback about the analysis</p>
            </div>
          ) : (
            comments.map((comment) => (
              <Card key={comment.id} className="border border-gray-200">
                <CardContent className="p-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      {getContextBadge(comment.context_type)}
                      {comment.context_reference && (
                        <span className="text-xs text-gray-500">
                          {comment.context_reference}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">
                      {formatRelativeTime(comment.created_at)}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-700 leading-relaxed">
                    {comment.content}
                  </p>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </ScrollArea>

      {/* Add Comment */}
      <div className="border-t border-gray-200 p-4 space-y-3">
        <Textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Add a comment or note..."
          className="resize-none"
          rows={3}
        />
        <Button 
          onClick={handleAddComment}
          disabled={!newComment.trim() || isAdding}
          size="sm"
          className="w-full"
        >
          <Plus className="h-4 w-4 mr-1" />
          {isAdding ? 'Adding...' : 'Add Comment'}
        </Button>
      </div>
    </div>
  )
}