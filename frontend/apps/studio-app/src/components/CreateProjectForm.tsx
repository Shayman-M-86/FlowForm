import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button, Input, LargeInput } from '@flowform/ui'

function toUrlSafeName(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

const createProjectSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  slug: z
    .string()
    .min(1, 'URL-safe name is required')
    .max(100)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Use lowercase letters, numbers, and hyphens only'),
  description: z.string().max(500).optional(),
})

type CreateProjectFields = z.infer<typeof createProjectSchema>

interface CreateProjectFormProps {
  onSubmit: (data: CreateProjectFields) => void
}

export function CreateProjectForm({ onSubmit }: CreateProjectFormProps) {
  const [urlSafeNameEdited, setUrlSafeNameEdited] = useState(false)
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CreateProjectFields>({
    resolver: zodResolver(createProjectSchema),
  })

  const name = watch('name')
  const urlSafeName = watch('slug')
  const urlSafeNameInput = register('slug')

  useEffect(() => {
    if (urlSafeNameEdited) return

    setValue('slug', toUrlSafeName(name ?? ''), {
      shouldDirty: true,
      shouldValidate: Boolean(name),
    })
  }, [name, setValue, urlSafeNameEdited])

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <Input
        label="Name"
        placeholder="My project"
        error={errors.name?.message}
        {...register('name')}
      />
      <Input
        label="URL-safe name"
        placeholder="my-project"
        hint="Used in the project URL. Use lowercase letters, numbers, and hyphens."
        error={errors.slug?.message}
        {...urlSafeNameInput}
        value={urlSafeName ?? ''}
        onChange={(event) => {
          setUrlSafeNameEdited(true)
          urlSafeNameInput.onChange(event)
        }}
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
