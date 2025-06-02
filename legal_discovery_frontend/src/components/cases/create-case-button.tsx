'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Plus } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'

interface CreateCaseData {
  case_title: string
  case_background: string
}

export function CreateCaseButton() {
  const [isOpen, setIsOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [background, setBackground] = useState('')
  const queryClient = useQueryClient()
  const router = useRouter()

  const createCaseMutation = useMutation({
    mutationFn: async (data: CreateCaseData) => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/cases`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        throw new Error('Failed to create case')
      }
      return response.json()
    },
    onSuccess: (newCase) => {
      // Invalidate and refetch cases
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      // Navigate to the new case
      router.push(`/cases/${newCase.id}`)
      // Reset form and close dialog
      setTitle('')
      setBackground('')
      setIsOpen(false)
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (title.trim() && background.trim().length >= 10) {
      createCaseMutation.mutate({
        case_title: title.trim(),
        case_background: background.trim()
      })
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          New Case
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Create New Legal Case</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Case Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Smith vs. TechCorp Contract Dispute"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="background">
              Case Background
              <span className="text-sm text-muted-foreground ml-2">
                ({background.trim().length}/10 min)
              </span>
            </Label>
            <Textarea
              id="background"
              value={background}
              onChange={(e) => setBackground(e.target.value)}
              placeholder="Provide detailed background information about the case, including key facts, parties involved, and legal issues... (minimum 10 characters)"
              className="min-h-[120px]"
              required
            />
          </div>
          <div className="flex justify-end space-x-2">
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => setIsOpen(false)}
              disabled={createCaseMutation.isPending}
            >
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={createCaseMutation.isPending || !title.trim() || background.trim().length < 10}
            >
              {createCaseMutation.isPending ? 'Creating...' : 'Create Case'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}