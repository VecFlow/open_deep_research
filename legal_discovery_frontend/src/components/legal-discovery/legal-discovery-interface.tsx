"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Progress } from "@/components/ui/progress"
import { 
  StreamMessage, 
  LegalDiscoveryResult, 
  AgentExecutionState,
  caseBackgroundSchema 
} from "@/lib/legal-discovery/types"
import { 
  streamLegalDiscovery, 
  getMessageTypeIcon, 
  getMessageTypeColor 
} from "@/lib/legal-discovery/utils"
import { cn } from "@/lib/utils"

export function LegalDiscoveryInterface() {
  const [caseBackground, setCaseBackground] = useState("")
  const [executionState, setExecutionState] = useState<AgentExecutionState>({
    isRunning: false,
    messages: [],
    result: null,
    error: null
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate input
    const validation = caseBackgroundSchema.safeParse({ case_background: caseBackground })
    if (!validation.success) {
      setExecutionState(prev => ({
        ...prev,
        error: validation.error.errors[0].message
      }))
      return
    }

    // Reset state and start execution
    setExecutionState({
      isRunning: true,
      messages: [],
      result: null,
      error: null
    })

    try {
      // Stream the legal discovery agent execution
      for await (const message of streamLegalDiscovery(caseBackground)) {
        setExecutionState(prev => ({
          ...prev,
          messages: [...prev.messages, message],
          result: message.type === 'complete' && message.data ? message.data : prev.result,
          error: message.type === 'error' ? message.message : prev.error
        }))

        // Stop execution on completion or error
        if (message.type === 'complete' || message.type === 'error') {
          setExecutionState(prev => ({ ...prev, isRunning: false }))
          break
        }
      }
    } catch (error) {
      console.error('Stream error:', error)
      setExecutionState(prev => ({
        ...prev,
        isRunning: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      }))
    }
  }

  const handleReset = () => {
    setExecutionState({
      isRunning: false,
      messages: [],
      result: null,
      error: null
    })
    setCaseBackground("")
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Input Form */}
      <Card>
        <CardHeader>
          <CardTitle>Case Background</CardTitle>
          <CardDescription>
            Provide details about your legal case for AI-powered discovery analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Textarea
              placeholder="Enter case background, facts, parties involved, potential issues, etc..."
              value={caseBackground}
              onChange={(e) => setCaseBackground(e.target.value)}
              className="min-h-[150px]"
              disabled={executionState.isRunning}
            />
            
            <div className="flex gap-2">
              <Button 
                type="submit" 
                disabled={executionState.isRunning || !caseBackground.trim()}
                className="flex-1"
              >
                {executionState.isRunning ? "🔄 Agent Running..." : "🚀 Start Discovery Analysis"}
              </Button>
              
              {(executionState.messages.length > 0 || executionState.error) && (
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={handleReset}
                  disabled={executionState.isRunning}
                >
                  Reset
                </Button>
              )}
            </div>

            {executionState.error && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-destructive text-sm">
                ❌ {executionState.error}
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Real-time Agent Execution Display */}
      {executionState.messages.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span>Agent Execution</span>
              {executionState.isRunning && <span className="animate-pulse">🔄</span>}
            </CardTitle>
            <CardDescription>
              Real-time legal discovery agent progress and insights
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {executionState.messages.map((message, index) => (
                <div
                  key={index}
                  className={cn(
                    "p-3 rounded-md border-l-4 text-sm",
                    message.type === 'error' ? 'bg-destructive/10 border-l-destructive' :
                    message.type === 'complete' ? 'bg-green-50 border-l-green-500' :
                    message.type === 'insight' ? 'bg-purple-50 border-l-purple-500' :
                    message.type === 'discovery' ? 'bg-yellow-50 border-l-yellow-500' :
                    'bg-muted border-l-muted-foreground'
                  )}
                >
                  <div className={cn("flex items-start gap-2", getMessageTypeColor(message.type))}>
                    <span className="text-base">{getMessageTypeIcon(message.type)}</span>
                    <div className="flex-1">
                      <div className="font-medium text-xs uppercase tracking-wide mb-1 opacity-70">
                        {message.type.replace('_', ' ')}
                      </div>
                      <div className="text-foreground whitespace-pre-wrap">
                        {message.message}
                      </div>
                      {message.case && (
                        <div className="mt-1 text-xs text-muted-foreground">
                          Case: {message.case}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Final Results Display */}
      {executionState.result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-green-600">🎯 Discovery Results</CardTitle>
            <CardDescription>
              Strategic deposition questions and insights generated by the AI agent
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Statistics */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-muted rounded-lg">
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {executionState.result.questions.length}
                  </div>
                  <div className="text-sm text-muted-foreground">Questions</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {(executionState.result.confidence_level * 100).toFixed(0)}%
                  </div>
                  <div className="text-sm text-muted-foreground">Confidence</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {executionState.result.evidence_sources}
                  </div>
                  <div className="text-sm text-muted-foreground">Evidence Sources</div>
                </div>
              </div>

              {/* Basis */}
              <div>
                <h4 className="font-semibold mb-2">Analysis Basis</h4>
                <p className="text-sm text-muted-foreground bg-muted p-3 rounded">
                  {executionState.result.basis}
                </p>
              </div>

              {/* Questions */}
              <div>
                <h4 className="font-semibold mb-3">Strategic Deposition Questions</h4>
                <div className="space-y-2">
                  {executionState.result.questions.map((question, index) => (
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