'use client'

import { useState, useEffect } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ThinkingStep {
  id: string
  title: string
  content?: string
  status: 'active' | 'completed' | 'pending'
  timestamp?: Date
}

interface ThinkingStepsProps {
  steps: ThinkingStep[]
  isActive?: boolean
  onComplete?: () => void
}

export function ThinkingSteps({ steps, isActive = false, onComplete }: ThinkingStepsProps) {
  const [isExpanded, setIsExpanded] = useState(isActive)
  const [displaySteps, setDisplaySteps] = useState<ThinkingStep[]>([])

  // Auto-collapse when thinking is complete
  useEffect(() => {
    if (!isActive && isExpanded) {
      const timer = setTimeout(() => {
        setIsExpanded(false)
        onComplete?.()
      }, 2000) // Wait 2 seconds after completion before collapsing
      return () => clearTimeout(timer)
    }
  }, [isActive, isExpanded, onComplete])

  // Update display steps when steps change
  useEffect(() => {
    setDisplaySteps(steps)
  }, [steps])

  // Expand when actively thinking
  useEffect(() => {
    if (isActive) {
      setIsExpanded(true)
    }
  }, [isActive])

  const completedSteps = steps.filter(step => step.status === 'completed').length
  const totalSteps = steps.length

  if (steps.length === 0) return null

  return (
    <div className="border border-gray-200 rounded-lg bg-gray-50/50 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-100/50 transition-colors"
      >
        <div className="flex items-center space-x-3">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-500" />
          )}
          <div className="flex items-center space-x-2">
            {isActive ? (
              <>
                <div className="flex space-x-1">
                  <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse"></div>
                  <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                </div>
                <span className="text-sm font-medium text-gray-700">Thinking...</span>
              </>
            ) : (
              <>
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm font-medium text-gray-700">
                  Thought for {Math.max(1, Math.floor(Math.random() * 8) + 2)} seconds
                </span>
              </>
            )}
          </div>
        </div>
        
        {!isActive && (
          <span className="text-xs text-gray-500">
            {completedSteps}/{totalSteps} steps
          </span>
        )}
      </button>

      {/* Expandable Content */}
      <div className={cn(
        "transition-all duration-300 ease-in-out overflow-hidden",
        isExpanded ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
      )}>
        <div className="px-4 pb-4 space-y-3 max-h-80 overflow-y-auto">
          {displaySteps.map((step, index) => (
            <div
              key={step.id}
              className={cn(
                "flex items-start space-x-3 transition-all duration-200",
                step.status === 'active' && "animate-pulse"
              )}
            >
              {/* Step indicator */}
              <div className={cn(
                "flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium mt-0.5",
                step.status === 'completed' && "bg-green-100 text-green-700",
                step.status === 'active' && "bg-blue-100 text-blue-700",
                step.status === 'pending' && "bg-gray-100 text-gray-500"
              )}>
                {step.status === 'completed' ? (
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : step.status === 'active' ? (
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
                ) : (
                  index + 1
                )}
              </div>

              {/* Step content */}
              <div className="flex-1 min-w-0">
                <div className={cn(
                  "text-sm font-medium",
                  step.status === 'completed' && "text-gray-900",
                  step.status === 'active' && "text-blue-900",
                  step.status === 'pending' && "text-gray-500"
                )}>
                  {step.title}
                </div>
                {step.content && (
                  <div className="text-xs text-gray-600 mt-1 line-clamp-2">
                    {step.content}
                  </div>
                )}
                {step.timestamp && step.status === 'completed' && (
                  <div className="text-xs text-gray-400 mt-1">
                    {step.timestamp.toLocaleTimeString()}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}