import { useState, type FormEvent } from 'react'

const EXAMPLE_QUESTIONS = [
  'Did younger and older worker pupae respond in the same direction, in terms of immune gene expression, when they were parasitized by Varroa mites?',
  'Among colony size, bee subspecies and apiary location, which of these significantly explained how much weight hives lost during one winter?',
]

type QuestionFormProps = {
  question?: string
  onQuestionChange?: (question: string) => void
  onSubmit: (question: string) => void
  isPending: boolean
}

const QUESTION_ERROR = 'Enter a question between 1 and 2,000 characters.'

export function QuestionForm({ question, onQuestionChange, onSubmit, isPending }: QuestionFormProps) {
  const [internalQuestion, setInternalQuestion] = useState('')
  const [validationMessage, setValidationMessage] = useState('')
  const currentQuestion = question ?? internalQuestion
  const characterCount = currentQuestion.length

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedQuestion = currentQuestion.trim()
    if (trimmedQuestion.length < 1 || trimmedQuestion.length > 2000) {
      setValidationMessage(QUESTION_ERROR)
      return
    }
    setValidationMessage('')
    onSubmit(trimmedQuestion)
  }

  return (
    <form className="question-form" onSubmit={submit}>
      <label htmlFor="research-question-input">Research question</label>
      <textarea
        id="research-question-input"
        name="question"
        rows={5}
        value={currentQuestion}
        disabled={isPending}
        aria-invalid={Boolean(validationMessage)}
        aria-describedby={validationMessage ? 'question-count question-error' : 'question-count'}
        onChange={(event) => {
          const nextQuestion = event.currentTarget.value
          if (onQuestionChange) onQuestionChange(nextQuestion)
          else setInternalQuestion(nextQuestion)
          if (validationMessage) setValidationMessage('')
        }}
      />
      <div className="question-form__meta">
        <span id="question-count" aria-live="polite">{characterCount.toLocaleString()} / 2,000</span>
        {validationMessage && <span id="question-error" className="field-error">{validationMessage}</span>}
      </div>
      <div className="question-form__examples" role="group" aria-label="Example questions">
        <span>Try an example:</span>
        {EXAMPLE_QUESTIONS.map((example) => (
          <button
            key={example}
            type="button"
            disabled={isPending}
            onClick={() => {
              if (onQuestionChange) onQuestionChange(example)
              else setInternalQuestion(example)
              setValidationMessage('')
            }}
          >
            {example}
          </button>
        ))}
      </div>
      <button className="primary-button" type="submit" disabled={isPending}>
        {isPending ? 'Searching…' : 'Search'}
      </button>
      {isPending && <p role="status">Retrieving passages and checking citations…</p>}
    </form>
  )
}
