"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ChevronUp, ChevronDown } from "lucide-react"
import {
  StreamMessage,
  LegalDiscoveryResult,
  caseBackgroundSchema
} from "@/lib/legal-discovery/types"
import { streamLegalDiscovery } from "@/lib/legal-discovery/utils"

interface StepData {
  title: string
  status: 'running' | 'completed' | 'error'
  substeps: SubStep[]
  isExpanded: boolean
}

interface SubStep {
  id: string
  type: string
  text: string
}

export function LegalDiscoveryInterface() {
  const [caseBackground, setCaseBackground] = useState("")
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [finalResult, setFinalResult] = useState<LegalDiscoveryResult | null>(null)
  const [steps, setSteps] = useState<StepData[]>([])
  const [initialAgentResponse, setInitialAgentResponse] = useState<string>("")

  const toggleStep = (index: number) => {
    setSteps(prev => prev.map((step, i) => 
      i === index ? { ...step, isExpanded: !step.isExpanded } : step
    ))
  }

  const processStream = (message: StreamMessage) => {
    // Handle agent introduction
    if (message.type === 'agent_intro') {
      setInitialAgentResponse(message.message)
      return
    }
    
    setSteps(prevSteps => {
      const newSteps = [...prevSteps]
      let currentStep = newSteps[newSteps.length - 1]

      // Determine if a new step should be created
      const isResearchPhase = message.type === 'research_progress' && message.message.includes('Round')
      const isFinalPhase = message.type === 'final_strategy' && message.message.includes('Compiling')
      
      let createdNewStep = false
      
      // Create new step only for major phase transitions
      if (!currentStep || 
          (isFinalPhase && currentStep.title !== "Generating Deposition Outline") ||
          (isResearchPhase && currentStep.title !== "Research Phase")) {
        
        if (currentStep) {
          currentStep.status = 'completed'
        }
        
        let title = "Investigation Phase"
        if (isResearchPhase) title = "Research Phase"
        if (isFinalPhase) title = "Generating Deposition Outline"

        currentStep = { 
          title, 
          status: 'running', 
          substeps: [],
          isExpanded: true
        }
        newSteps.push(currentStep)
        createdNewStep = true
      }

      if (!createdNewStep) {
        // Check if this substep already exists to prevent duplicates
        const isDuplicate = currentStep.substeps.some(existing => 
          existing.type === message.type && existing.text === message.message
        )
        
        if (!isDuplicate) {
          const newSubStep: SubStep = {
            id: crypto.randomUUID(),
            type: message.type,
            text: message.message
          }
          currentStep.substeps.push(newSubStep)
        }
      }

      // Handle completion or error
      if (message.type === 'complete') {
        currentStep.status = 'completed'
        setFinalResult(message.data || null)
        setIsRunning(false)
      }
      if (message.type === 'error') {
        currentStep.status = 'error'
        setError(message.message)
        setIsRunning(false)
      }

      return newSteps
    })
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const validation = caseBackgroundSchema.safeParse({ case_background: caseBackground })
    if (!validation.success) {
      setError(validation.error.errors[0].message)
      return
    }

    setIsRunning(true)
    setError(null)
    setFinalResult(null)
    setSteps([])
    setInitialAgentResponse("")

    try {
      for await (const message of streamLegalDiscovery(caseBackground)) {
        processStream(message)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred'
      setError(errorMessage)
      setSteps(prev => {
        const lastStep = prev[prev.length - 1]
        if (lastStep) lastStep.status = 'error'
        return [...prev]
      })
    } finally {
      setIsRunning(false)
    }
  }

  const handleReset = () => {
    setIsRunning(false)
    setError(null)
    setFinalResult(null)
    setSteps([])
    setInitialAgentResponse("")
    setCaseBackground("")
  }

  const getSubstepIcon = (type: string) => {
    switch (type) {
      case 'search':
      case 'research_progress':
        return '🔍'
      case 'browsing':
      case 'insight':
      case 'discovery':
        return '🔗'
      default:
        return '📄'
    }
  }

  return (
    <div className="space-y-6">
      {/* Input Section - Clean and minimal */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Case Background
          </label>
          <Textarea
            placeholder="Provide details about your legal case for AI-powered discovery analysis..."
            value={caseBackground}
            onChange={(e) => setCaseBackground(e.target.value)}
            className="min-h-[120px] border-gray-200 focus:border-gray-400 focus:ring-0 resize-none"
            disabled={isRunning}
          />
        </div>
        
        <div className="flex gap-3">
          <Button 
            onClick={handleSubmit} 
            disabled={isRunning || !caseBackground.trim()}
            className="bg-gray-900 hover:bg-gray-800 text-white px-6 py-2 rounded-md"
          >
            {isRunning ? "Agent Running..." : "Start Discovery Analysis"}
          </Button>
          
          {(steps.length > 0 || error) && (
            <Button 
              variant="outline" 
              onClick={handleReset} 
              disabled={isRunning}
              className="border-gray-200 text-gray-700 hover:bg-gray-50"
            >
              Reset
            </Button>
          )}
        </div>
        
        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md border border-red-200">
            {error}
          </div>
        )}
      </div>

      {/* Agent Response Section - Manus Style */}
      {(initialAgentResponse || steps.length > 0) && (
        <div className="space-y-6 pt-6">
          {/* Initial Agent Response */}
          {initialAgentResponse && (
            <div className="text-gray-800 leading-relaxed">
              {initialAgentResponse}
            </div>
          )}
          
          {/* Steps - Manus Style */}
          {steps.map((step, index) => (
            <div key={index} className="space-y-3">
              {/* Step Header */}
              <div className="flex items-center gap-3">
                <div className="text-gray-400">
                  {step.status === 'completed' ? '✓' : step.status === 'running' ? '◯' : '✗'}
                </div>
                <button
                  onClick={() => toggleStep(index)}
                  className="flex items-center gap-2 text-gray-900 hover:text-gray-700 transition-colors"
                >
                  <span className="font-medium">{step.title}</span>
                  {step.isExpanded ? 
                    <ChevronUp className="w-4 h-4 text-gray-400" /> : 
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  }
                </button>
              </div>

              {/* Step Content */}
              {step.isExpanded && (
                <div className="ml-8 space-y-3 border-l border-gray-100 pl-6">
                  {step.substeps.map((substep) => (
                    <div key={substep.id} className="flex items-start gap-3">
                      <span className="text-sm mt-0.5">{getSubstepIcon(substep.type)}</span>
                      <div className="flex-1">
                        {substep.type === 'search' || substep.type === 'research_progress' ? (
                          <div className="bg-gray-50 px-3 py-2 rounded-md">
                            <span className="text-sm text-gray-600">
                              {substep.type === 'search' ? 'Searching' : 'Researching'} <span className="text-gray-400 font-mono text-xs">{substep.text}</span>
                            </span>
                          </div>
                        ) : substep.type === 'browsing' ? (
                          <div className="bg-gray-50 px-3 py-2 rounded-md">
                            <span className="text-sm text-gray-600">
                              Browsing <span className="text-gray-400 font-mono text-xs">{substep.text}</span>
                            </span>
                          </div>
                        ) : (
                          <div className="text-sm text-gray-700 leading-relaxed">
                            {substep.text}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      
      {/* Final Results - Clean styling */}
      {finalResult && (
        <div className="mt-8 p-6 bg-green-50 border border-green-200 rounded-lg">
          <h3 className="text-lg font-medium text-green-800 mb-4">Discovery Results</h3>
          
          <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-white rounded-md">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{finalResult.questions.length}</div>
              <div className="text-sm text-gray-600">Questions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {(finalResult.confidence_level * 100).toFixed(0)}%
              </div>
              <div className="text-sm text-gray-600">Confidence</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{finalResult.evidence_sources}</div>
              <div className="text-sm text-gray-600">Evidence Sources</div>
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Analysis Basis</h4>
              <p className="text-sm text-gray-700 bg-white p-3 rounded-md">
                {finalResult.basis}
              </p>
            </div>
            
            <div>
              <h4 className="font-medium text-gray-900 mb-3">Strategic Deposition Questions</h4>
              <div className="space-y-2">
                {finalResult.questions.map((question, index) => (
                  <div key={index} className="flex gap-3 p-3 bg-white rounded-md">
                    <span className="flex-shrink-0 w-6 h-6 bg-green-600 text-white text-xs font-bold rounded-full flex items-center justify-center">
                      {index + 1}
                    </span>
                    <div className="text-sm text-gray-700">{question}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
} 