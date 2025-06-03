'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ThinkingSteps } from './thinking-steps'
import { FeedbackButtons } from './feedback-buttons'
import { MarkdownRenderer } from '@/components/ui/markdown-renderer'
import { useCaseAnalysis } from '@/lib/cases/queries'
import { useAnalysisWorkflow } from '@/lib/analysis/queries'
import { useWorkflowControl, useStartAnalysis } from '@/lib/analysis/mutations'
import { Send, Play, Pause, Square, Sparkles, Clock } from 'lucide-react'
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
  thinkingSteps?: Array<{
    id: string
    title: string
    content?: string
    status: 'active' | 'completed' | 'pending'
    timestamp?: Date
  }>
  isThinking?: boolean
}

export function ChatInterface({ caseId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [currentThinkingSteps, setCurrentThinkingSteps] = useState<any[]>([])
  const [isThinking, setIsThinking] = useState(false)
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
      ws.send(JSON.stringify({ 
        type: 'subscribe_case', 
        case_id: caseId 
      }))
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
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
    const messageId = `msg_${Date.now()}`
    
    // Handle thinking steps for progress updates
    if (update.type === 'progress_update' && update.message) {
      const step = {
        id: `step_${Date.now()}`,
        title: update.message,
        status: 'active' as const,
        timestamp: new Date()
      }
      
      setIsThinking(true)
      setCurrentThinkingSteps(prev => [...prev, step])
      return
    }

    // Handle other message types
    let content = ''
    let type: 'assistant' | 'system' | 'user' = 'system'
    let shouldCreateMessage = true
    
    switch (update.type) {
      case 'feedback_requested':
        content = update.message
        type = 'system'
        setIsThinking(false)
        // Mark all current thinking steps as completed
        setCurrentThinkingSteps(prev => 
          prev.map(step => ({ ...step, status: 'completed' as const }))
        )
        break
        
      case 'analysis_completed':
        const analysisContent = update.final_analysis || 'Analysis completed but no content received.'
        const completedCount = update.completed_categories?.length || 0
        const depositionQuestions = update.deposition_questions
        
        content = `# Legal Analysis Complete\n\n**Categories Analyzed:** ${completedCount}\n\n## Analysis Results\n\n${analysisContent}`
        
        if (depositionQuestions) {
          if (typeof depositionQuestions === 'string') {
            content += `\n\n## Deposition Questions\n\n${depositionQuestions}`
          } else if (typeof depositionQuestions === 'object') {
            content += `\n\n## Deposition Questions\n\n\`\`\`json\n${JSON.stringify(depositionQuestions, null, 2)}\n\`\`\``
          }
        }
        
        type = 'assistant'
        setIsThinking(false)
        setCurrentThinkingSteps(prev => 
          prev.map(step => ({ ...step, status: 'completed' as const }))
        )
        break
        
      default:
        if (update.message) {
          content = update.message
          type = 'system'
        } else {
          shouldCreateMessage = false
        }
    }
    
    if (shouldCreateMessage && content) {
      // If we have thinking steps, attach them to this message
      const finalThinkingSteps = isThinking ? [] : currentThinkingSteps
      
      const newMessage: ChatMessage = {
        id: messageId,
        type,
        content,
        timestamp: new Date(),
        metadata: update,
        thinkingSteps: finalThinkingSteps.length > 0 ? finalThinkingSteps : undefined,
        isThinking: false
      }
      
      setMessages(prev => [...prev, newMessage])
      
      // Clear thinking steps after attaching them
      if (!isThinking) {
        setCurrentThinkingSteps([])
      }
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
    
    if (input.toLowerCase().includes('start analysis')) {
      await handleStartAnalysis()
    } else {
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
      if (!analysisId) return
      
      await workflowControl.mutateAsync({
        caseId: analysisId,
        action: 'feedback',
        feedback
      })
    } catch (error) {
      console.error('Failed to send feedback:', error)
    }
  }

  const handleFeedbackSubmit = async (feedback: string, approved: boolean) => {
    try {
      const analysisId = caseData?.analyses?.[0]?.id
      if (!analysisId) return
      
      await workflowControl.mutateAsync({
        caseId: analysisId,
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
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <Sparkles className="h-5 w-5 text-blue-600" />
              <h1 className="text-lg font-semibold text-gray-900">Legal Analysis</h1>
            </div>
            <div className={cn(
              "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium",
              isConnected 
                ? "bg-green-100 text-green-700" 
                : "bg-red-100 text-red-700"
            )}>
              <div className={cn(
                "w-2 h-2 rounded-full mr-1.5",
                isConnected ? "bg-green-500" : "bg-red-500"
              )} />
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {(!workflowStatus || workflowStatus.status === 'draft' || workflowStatus.status === 'pending') && (
              <Button
                size="sm"
                onClick={handleStartAnalysis}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                <Play className="h-4 w-4 mr-1" />
                Start Analysis
              </Button>
            )}
            
            {workflowStatus?.status === 'in_progress' && (
              <Button variant="outline" size="sm">
                <Pause className="h-4 w-4 mr-1" />
                Pause
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto px-6 py-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 && (
              <div className="text-center py-12">
                <Sparkles className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Ready to analyze your case
                </h3>
                <p className="text-gray-500 mb-6">
                  Start a conversation to begin your comprehensive legal analysis
                </p>
                <Button
                  onClick={() => setInput('Start analysis for this case')}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Start Analysis
                </Button>
              </div>
            )}
            
            {messages.map((message) => (
              <div key={message.id} className="group">
                {/* Message */}
                <div className={cn(
                  "flex items-start space-x-4",
                  message.type === 'user' && "flex-row-reverse space-x-reverse"
                )}>
                  {/* Avatar */}
                  <div className={cn(
                    "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
                    message.type === 'user' 
                      ? "bg-blue-600 text-white" 
                      : message.type === 'assistant'
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-600"
                  )}>
                    {message.type === 'user' ? 'U' : message.type === 'assistant' ? 'A' : 'S'}
                  </div>
                  
                  {/* Content */}
                  <div className={cn(
                    "flex-1 space-y-3",
                    message.type === 'user' && "text-right"
                  )}>
                    {/* Thinking Steps */}
                    {message.thinkingSteps && message.thinkingSteps.length > 0 && (
                      <ThinkingSteps 
                        steps={message.thinkingSteps}
                        isActive={false}
                      />
                    )}
                    
                    {/* Message Content */}
                    <div className={cn(
                      "prose prose-gray max-w-none",
                      message.type === 'user' && "text-right"
                    )}>
                      {message.type === 'assistant' ? (
                        <MarkdownRenderer content={message.content} />
                      ) : (
                        <p className="text-gray-700 leading-relaxed">
                          {message.content}
                        </p>
                      )}
                    </div>
                    
                    {/* Feedback Buttons */}
                    {message.metadata?.type === 'feedback_requested' && (
                      <div className="mt-4">
                        <FeedbackButtons
                          onFeedback={handleFeedbackSubmit}
                          categories={message.metadata?.categories || []}
                        />
                      </div>
                    )}
                    
                    {/* Timestamp */}
                    <div className={cn(
                      "text-xs text-gray-400",
                      message.type === 'user' && "text-right"
                    )}>
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </div>
            ))}
            
            {/* Active Thinking Steps */}
            {isThinking && currentThinkingSteps.length > 0 && (
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-medium">
                  A
                </div>
                <div className="flex-1">
                  <ThinkingSteps 
                    steps={currentThinkingSteps}
                    isActive={true}
                  />
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      {/* Input */}
      <div className="flex-shrink-0 border-t border-gray-200 bg-white px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="relative">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Legal AI..."
              className="w-full resize-none border-gray-300 rounded-xl pr-12 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={1}
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
              size="sm"
              className="absolute right-2 bottom-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <div className="text-xs text-gray-500 mt-2 text-center">
            Legal AI can make mistakes. Consider checking important information.
          </div>
        </div>
      </div>
    </div>
  )
}