import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button, Input, LargeInput } from '@flowform/ui'

const createProjectSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  description: z.string().max(500).optional(),
})

type CreateProjectFields = z.infer<typeof createProjectSchema>

interface CreateProjectFormProps {
  onSubmit: (data: CreateProjectFields) => void
}

export function CreateProjectForm({ onSubmit }: CreateProjectFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateProjectFields>({
    resolver: zodResolver(createProjectSchema),
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <Input
        label="Name"
        placeholder="My project"
        error={errors.name?.message}
        {...register('name')}
      />
      <LargeInput
        label="Description"
        error={errors.description?.message}
        autoGrow
        {...register('description')}
      />
      <div>
        <Button variant="primary" disabled={isSubmitting}>
          {isSubmitting ? 'Creating…' : 'Create project'}
        </Button>
      </div>
    </form>
  )
}
