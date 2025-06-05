"use client"

import * as React from 'react'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { CheckCircle2, Loader, XCircle, FileText, Search, Lightbulb, BrainCircuit } from 'lucide-react'
import { cn } from '@/lib/utils'

export type StepStatus = "running" | "completed" | "error" | "pending";

export interface SubStep {
  id: string;
  type: string;
  text: string;
}

export interface AgentStepProps {
  title: string;
  status: StepStatus;
  substeps: SubStep[];
}

const statusIcons: Record<StepStatus, React.ReactNode> = {
  running: <Loader className="h-5 w-5 animate-spin text-blue-500" />,
  completed: <CheckCircle2 className="h-5 w-5 text-green-500" />,
  error: <XCircle className="h-5 w-5 text-red-500" />,
  pending: <FileText className="h-5 w-5 text-gray-400" />,
};

const substepIcons: Record<string, React.ReactNode> = {
  search: <Search className="h-4 w-4 text-blue-500" />,
  insight: <Lightbulb className="h-4 w-4 text-yellow-500" />,
  discovery: <Lightbulb className="h-4 w-4 text-yellow-500" />,
  progress: <BrainCircuit className="h-4 w-4 text-purple-500" />,
  default: <FileText className="h-4 w-4 text-gray-500" />,
}

export function AgentStep({ title, status, substeps }: AgentStepProps) {
  return (
    <Accordion type="single" collapsible className="w-full" defaultValue="step-item">
      <AccordionItem value="step-item" className="border rounded-lg px-4 bg-card">
        <AccordionTrigger>
          <div className="flex items-center gap-3">
            {statusIcons[status]}
            <span className={cn(
              "font-semibold",
              status === 'error' && 'text-red-500',
              status === 'completed' && 'text-green-500'
            )}>{title}</span>
          </div>
        </AccordionTrigger>
        <AccordionContent>
          <div className="pl-8 space-y-2 border-l border-dashed ml-2.5">
            {substeps.map((substep, index) => (
              <div key={substep.id} className="flex items-start gap-3 text-sm">
                <div className="mt-1">
                  {substepIcons[substep.type] || substepIcons.default}
                </div>
                <p className="text-muted-foreground">{substep.text}</p>
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
} 