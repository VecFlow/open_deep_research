"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { AgentStep, AgentStepProps, SubStep, StepStatus } from "@/components/legal-discovery/agent-step"
import {
  StreamMessage,
  LegalDiscoveryResult,
  caseBackgroundSchema
} from "@/lib/legal-discovery/types"
import { streamLegalDiscovery } from "@/lib/legal-discovery/utils"

export function LegalDiscoveryInterface() {
  const [caseBackground, setCaseBackground] = useState("")
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [finalResult, setFinalResult] = useState<LegalDiscoveryResult | null>(null)
  const [steps, setSteps] = useState<AgentStepProps[]>([])

  const processStream = (message: StreamMessage) => {
    console.log('Processing message:', message.type, message.message.substring(0, 50) + '...');
    
    setSteps(prevSteps => {
      console.log('Current steps count:', prevSteps.length);
      const newSteps = [...prevSteps]
      let currentStep = newSteps[newSteps.length - 1]

      // Determine if a new step should be created
      const isNewResearchRound = message.type === 'research_progress' && message.message.includes('Round')
      const isFinalPhase = message.type === 'final_strategy' && message.message.includes('Compiling')
      
      // Track if we created a new step
      let createdNewStep = false
      
      if (!currentStep || isNewResearchRound || isFinalPhase) {
        if (currentStep) {
          currentStep.status = 'completed'
        }
        
        let title = "Agent Initializing..."
        if (isNewResearchRound) title = `Research Round ${message.message.split(' ')[2]}`
        if (isFinalPhase) title = "Generating Deposition Outline"

        console.log('Creating new step:', title);
        currentStep = { title, status: 'running', substeps: [] }
        newSteps.push(currentStep)
        createdNewStep = true
      }

      // Only add substep if we didn't just create a new step with this message
      // This prevents duplication of trigger messages
      if (!createdNewStep) {
        console.log('Adding substep to step:', currentStep.title);
        const newSubStep: SubStep = {
          id: crypto.randomUUID(),
          type: message.type,
          text: message.message
        }
        currentStep.substeps.push(newSubStep)
        console.log('Step now has', currentStep.substeps.length, 'substeps');
      } else {
        console.log('Skipping substep addition - new step was created');
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

    // Reset state and start execution
    setIsRunning(true)
    setError(null)
    setFinalResult(null)
    setSteps([{ title: "Initial Investigation", status: "running", substeps: [] }])

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
    setCaseBackground("")
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Case Background</CardTitle>
          <CardDescription>
            Provide details about your legal case for AI-powered discovery analysis.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Textarea
              placeholder="Enter case background, facts, parties involved, potential issues, etc..."
              value={caseBackground}
              onChange={(e) => setCaseBackground(e.target.value)}
              className="min-h-[150px]"
              disabled={isRunning}
            />
            <div className="flex gap-2">
              <Button type="submit" disabled={isRunning || !caseBackground.trim()} className="flex-1">
                {isRunning ? "🔄 Agent Running..." : "🚀 Start Discovery Analysis"}
              </Button>
              {(steps.length > 0 || error) && (
                <Button type="button" variant="outline" onClick={handleReset} disabled={isRunning}>
                  Reset
                </Button>
              )}
            </div>
            {error && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-destructive text-sm">
                ❌ {error}
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      {steps.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">Agent Activity</h2>
          {steps.map((step, index) => (
            <AgentStep key={index} {...step} />
          ))}
        </div>
      )}
      
      {finalResult && (
        <Card>
          <CardHeader>
            <CardTitle className="text-green-600">🎯 Discovery Results</CardTitle>
            <CardDescription>
              Strategic deposition questions and insights generated by the AI agent.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4 p-4 bg-muted rounded-lg">
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {finalResult.questions.length}
                  </div>
                  <div className="text-sm text-muted-foreground">Questions</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {(finalResult.confidence_level * 100).toFixed(0)}%
                  </div>
                  <div className="text-sm text-muted-foreground">Confidence</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {finalResult.evidence_sources}
                  </div>
                  <div className="text-sm text-muted-foreground">Evidence Sources</div>
                </div>
              </div>
              <div>
                <h4 className="font-semibold mb-2">Analysis Basis</h4>
                <p className="text-sm text-muted-foreground bg-muted p-3 rounded">
                  {finalResult.basis}
                </p>
              </div>
              <div>
                <h4 className="font-semibold mb-3">Strategic Deposition Questions</h4>
                <div className="space-y-2">
                  {finalResult.questions.map((question, index) => (
                    <div key={index} className="p-3 border rounded-md bg-card">
                      <div className="flex items-start gap-3">
                        <span className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground text-xs font-bold rounded-full flex items-center justify-center">
                          {index + 1}
                        </span>
                        <div className="text-sm">{question}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 