import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button, Input, LargeInput, Select } from '@flowform/ui'
import { useRenderDebug } from '@/debug/useRenderDebug'

function toUrlSafeName(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

const createSurveySchema = z.object({
  title: z.string().min(1, 'Name is required').max(100),
  slug: z
    .string()
    .min(1, 'URL-safe name is required')
    .max(100)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Use lowercase letters, numbers, and hyphens only'),
  description: z.string().max(500).optional(),
  initialStatus: z.enum(['draft', 'published']),
})

export type CreateSurveyFields = z.infer<typeof createSurveySchema>

interface CreateSurveyFormProps {
  onSubmit: (data: CreateSurveyFields) => void
}

const initialStatusOptions = [
  { value: 'draft', label: 'Draft' },
  { value: 'published', label: 'Published' },
]

export function CreateSurveyForm({ onSubmit }: CreateSurveyFormProps) {
  useRenderDebug('CreateSurveyForm', { onSubmit })
  const [slugEdited, setSlugEdited] = useState(false)
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    control,
    formState: { errors, isSubmitting },
  } = useForm<CreateSurveyFields>({
    resolver: zodResolver(createSurveySchema),
    mode: 'onTouched',
    defaultValues: { initialStatus: 'draft' },
  })

  const title = watch('title')
  const slug = watch('slug')
  const slugInput = register('slug')

  useEffect(() => {
    if (slugEdited) return
    setValue('slug', toUrlSafeName(title ?? ''), {
      shouldDirty: true,
      shouldValidate: Boolean(title),
    })
  }, [title, setValue, slugEdited])

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <Input
        label="Name"
        placeholder="My survey"
        error={errors.title?.message}
        {...register('title')}
      />
      <Input
        label="URL-safe name"
        placeholder="my-survey"
        hint="Used in the survey URL. Use lowercase letters, numbers, and hyphens."
        error={errors.slug?.message}
        {...slugInput}
        value={slug ?? ''}
        onChange={(event) => {
          setSlugEdited(true)
          slugInput.onChange(event)
        }}
      />
      <LargeInput
        label="Description"
        error={errors.description?.message}
        autoGrow
        {...register('description')}
      />
      <Controller
        control={control}
        name="initialStatus"
        render={({ field }) => (
          <Select
            label="Initial status"
            options={initialStatusOptions}
            value={field.value}
            onValueChange={field.onChange}
            error={errors.initialStatus?.message}
          />
        )}
      />
      <div>
        <Button variant="primary" disabled={isSubmitting}>
          {isSubmitting ? 'Creating…' : 'Create survey'}
        </Button>
      </div>
    </form>
  )
}
