'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { FeedbackButtons } from './feedback-buttons'
import { ThinkingSteps } from './thinking-steps'
import { CategoryProgress } from './category-progress'
import { CommentsPanel } from './comments-panel'
import { useCaseAnalysis } from '@/lib/cases/queries'
import { useAnalysisWorkflow } from '@/lib/analysis/queries'
import { useWorkflowControl, useStartAnalysis } from '@/lib/analysis/mutations'
import { Send, Pause, Play, Square, MessageCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatInterfaceProps {
  caseId: string
}

interface ChatMessage {
  id: string
  type: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  metadata?: any
}

export function ChatInterface({ caseId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [showComments, setShowComments] = useState(false)
  const [analysisResults, setAnalysisResults] = useState<any>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const { data: caseData } = useCaseAnalysis(caseId)
  const { data: workflowStatus } = useAnalysisWorkflow(caseId)
  const workflowControl = useWorkflowControl()
  const startAnalysis = useStartAnalysis()
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }
  
  useEffect(() => {
    scrollToBottom()
  }, [messages])
  
  // WebSocket connection for real-time updates
  useEffect(() => {
    const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`)
    
    ws.onopen = () => {
      setIsConnected(true)
      // Subscribe to case updates
      ws.send(JSON.stringify({ 
        type: 'subscribe_case', 
        case_id: caseId 
      }))
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('🔍 WebSocket message received:', data)
      handleWorkflowUpdate(data)
    }
    
    ws.onclose = () => {
      setIsConnected(false)
    }
    
    return () => {
      ws.close()
    }
  }, [caseId])
  
  const handleWorkflowUpdate = (update: any) => {
    console.log('🔄 Processing workflow update:', update)
    const messageId = `msg_${Date.now()}`
    
    let content = ''
    let type: 'assistant' | 'system' = 'assistant'
    let shouldCreateMessage = true
    
    switch (update.type) {
      case 'plan_generated':
        content = `Analysis plan generated with ${update.total_categories} categories.`
        type = 'system'
        break
      case 'feedback_requested':
        content = update.message
        type = 'system'
        break
      case 'category_completed':
        content = `Completed analysis for: ${update.categories.map((c: any) => c.name).join(', ')}`
        type = 'system'
        break
      case 'deposition_generated':
        content = 'Deposition questions have been generated.'
        type = 'system'
        break
      case 'analysis_completed':
        // Display the final analysis content instead of just a summary
        const analysisContent = update.final_analysis || 'Analysis completed but no content received.'
        const completedCount = update.completed_categories?.length || 0
        const depositionQuestions = update.deposition_questions
        
        // Store the analysis results for the progress display
        setAnalysisResults({
          completed_categories: update.completed_categories || [],
          total_categories: completedCount,
          final_analysis: update.final_analysis,
          deposition_questions: update.deposition_questions
        })
        
        content = `🎉 **Legal Analysis Complete!**\n\n**Categories Analyzed:** ${completedCount}\n\n**Analysis Results:**\n\n${analysisContent}`
        
        // Add deposition questions if available
        if (depositionQuestions && typeof depositionQuestions === 'string') {
          content += `\n\n**Deposition Questions:**\n\n${depositionQuestions}`
        } else if (depositionQuestions && typeof depositionQuestions === 'object') {
          content += `\n\n**Deposition Questions:**\n\n${JSON.stringify(depositionQuestions, null, 2)}`
        }
        
        type = 'assistant'
        break
      case 'progress_update':
        if (update.message) {
          content = update.message
          type = 'system'
        } else {
          shouldCreateMessage = false
        }
        break
      case 'error':
        content = `Error: ${update.message}`
        type = 'system'
        break
      default:
        // Only create messages for known types or those with explicit content
        if (update.message) {
          content = `Workflow update: ${update.type}`
          type = 'system'
        } else {
          shouldCreateMessage = false
        }
    }
    
    if (shouldCreateMessage && content) {
      const newMessage: ChatMessage = {
        id: messageId,
        type,
        content,
        timestamp: new Date(),
        metadata: update
      }
      
      setMessages(prev => [...prev, newMessage])
    }
  }
  
  const handleSendMessage = async () => {
    if (!input.trim()) return
    
    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      type: 'user',
      content: input,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMessage])
    
    // Handle different types of user input
    if (input.toLowerCase().includes('start analysis')) {
      await handleStartAnalysis()
    } else {
      // Handle as feedback or comment
      await handleUserFeedback(input)
    }
    
    setInput('')
  }
  
  const handleStartAnalysis = async () => {
    try {
      await startAnalysis.mutateAsync(caseId)
      
      const systemMessage: ChatMessage = {
        id: `system_${Date.now()}`,
        type: 'system',
        content: 'Starting legal analysis...',
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, systemMessage])
    } catch (error) {
      console.error('Failed to start analysis:', error)
    }
  }
  
  const handleUserFeedback = async (feedback: string) => {
    try {
      const analysisId = caseData?.analyses?.[0]?.id
      if (!analysisId) {
        console.error('No analysis ID found')
        return
      }
      
      await workflowControl.mutateAsync({
        caseId: analysisId, // Use analysisId instead of caseId
        action: 'feedback',
        feedback
      })
    } catch (error) {
      console.error('Failed to send feedback:', error)
    }
  }
  
  const handleWorkflowControl = async (action: 'pause' | 'resume' | 'stop') => {
    try {
      const analysisId = caseData?.analyses?.[0]?.id
      if (!analysisId) {
        console.error('No analysis ID found')
        return
      }
      
      await workflowControl.mutateAsync({
        caseId: analysisId, // Use analysisId instead of caseId
        action
      })
      
      const systemMessage: ChatMessage = {
        id: `system_${Date.now()}`,
        type: 'system',
        content: `Workflow ${action}ed.`,
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, systemMessage])
    } catch (error) {
      console.error(`Failed to ${action} workflow:`, error)
    }
  }
  
  const handleFeedbackSubmit = async (feedback: string, approved: boolean) => {
    try {
      const analysisId = caseData?.analyses?.[0]?.id
      if (!analysisId) {
        console.error('No analysis ID found')
        return
      }
      
      await workflowControl.mutateAsync({
        caseId: analysisId, // Use analysisId instead of caseId
        action: 'feedback',
        feedback,
        approve: approved
      })
      
      const systemMessage: ChatMessage = {
        id: `system_${Date.now()}`,
        type: 'system',
        content: approved ? 'Plan approved. Continuing analysis...' : 'Feedback provided. Regenerating plan...',
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, systemMessage])
    } catch (error) {
      console.error('Failed to provide feedback:', error)
    }
  }
  
  return (
    <div className="h-full flex">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <h2 className="text-lg font-semibold text-gray-900">
                Legal Analysis Chat
              </h2>
              <Badge 
                variant={isConnected ? 'default' : 'destructive'}
                className="text-xs"
              >
                {isConnected ? 'Connected' : 'Disconnected'}
              </Badge>
            </div>
            
            <div className="flex items-center space-x-2">
              {/* Show Start Analysis button if no analysis has started */}
              {(!workflowStatus || workflowStatus.status === 'draft' || workflowStatus.status === 'pending') && (
                <Button
                  size="sm"
                  onClick={handleStartAnalysis}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  <Play className="h-4 w-4 mr-1" />
                  Start Analysis
                </Button>
              )}
              
              {workflowStatus?.status === 'in_progress' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleWorkflowControl('pause')}
                >
                  <Pause className="h-4 w-4 mr-1" />
                  Pause
                </Button>
              )}
              
              {workflowStatus?.status === 'paused' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleWorkflowControl('resume')}
                >
                  <Play className="h-4 w-4 mr-1" />
                  Resume
                </Button>
              )}
              
              {(workflowStatus?.status === 'in_progress' || workflowStatus?.status === 'paused') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleWorkflowControl('stop')}
                >
                  <Square className="h-4 w-4 mr-1" />
                  Stop
                </Button>
              )}
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowComments(!showComments)}
              >
                <MessageCircle className="h-4 w-4 mr-1" />
                Comments
              </Button>
            </div>
          </div>
        </div>
        
        {/* Messages */}
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-8">
                <p className="text-gray-500">
                  Start a conversation to begin your legal analysis
                </p>
                <Button
                  className="mt-4"
                  onClick={() => setInput('Start analysis for this case')}
                >
                  Start Analysis
                </Button>
              </div>
            )}
            
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'chat-message',
                  message.type === 'user' && 'user',
                  message.type === 'assistant' && 'assistant',
                  message.type === 'system' && 'system'
                )}
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-1">
                    <p className="text-sm">{message.content}</p>
                    <span className="text-xs text-gray-400 mt-1">
                      {message.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                </div>
                
                {/* Show feedback buttons for feedback requests */}
                {message.metadata?.type === 'feedback_requested' && (
                  <div className="mt-3">
                    <FeedbackButtons
                      onFeedback={handleFeedbackSubmit}
                      categories={message.metadata?.categories || caseData?.analyses?.[0]?.categories || []}
                    />
                  </div>
                )}
                
                {/* Show thinking steps for analysis updates */}
                {message.metadata?.type === 'category_completed' && (
                  <div className="mt-3">
                    <ThinkingSteps
                      categories={message.metadata.categories}
                      currentStep="analysis"
                    />
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
        
        {/* Input */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex space-x-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message or provide feedback..."
              className="flex-1 resize-none"
              rows={3}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSendMessage()
                }
              }}
            />
            <Button 
              onClick={handleSendMessage}
              disabled={!input.trim() || !isConnected}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
      
      {/* Side Panel */}
      <div className="w-80 border-l border-gray-200 flex flex-col">
        {/* Category Progress */}
        <div className="border-b border-gray-200 p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-3">
            Analysis Progress
          </h3>
          <CategoryProgress 
            categories={analysisResults?.completed_categories || caseData?.analyses?.[0]?.categories || []}
            progress={analysisResults ? 
              analysisResults.completed_categories.map((cat: any, index: number) => ({
                category: cat.name || `Category ${index + 1}`,
                status: 'completed',
                content: cat.content || ''
              })) : 
              (caseData?.analyses?.[0]?.category_progress || [])
            }
          />
        </div>
        
        {/* Comments Panel */}
        {showComments && (
          <div className="flex-1">
            <CommentsPanel caseId={caseId} />
          </div>
        )}
      </div>
    </div>
  )
}