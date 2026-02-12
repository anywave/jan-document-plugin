import { useState } from 'react'

interface GlobalErrorProps {
  error: Error | unknown
}

export default function GlobalError({ error }: GlobalErrorProps) {
  console.error('Error in root route:', error)
  const [showFull, setShowFull] = useState(false)

  const errorMessage = error instanceof Error ? error.message : String(error)
  const errorStack = error instanceof Error ? error.stack || '' : ''

  const handleReportBug = () => {
    const title = encodeURIComponent(`[Bug] App crash: ${errorMessage.slice(0, 80)}`)
    const body = encodeURIComponent(
      `## Description\nMOBIUS crashed with an unexpected error.\n\n` +
      `## Error\n\`\`\`\n${errorMessage}\n\`\`\`\n\n` +
      `## Stack Trace\n\`\`\`\n${errorStack.slice(0, 1500)}\n\`\`\`\n\n` +
      `## Environment\n- Platform: ${navigator.platform}\n- User Agent: ${navigator.userAgent}\n`
    )
    window.open(
      `https://github.com/anywave/jan-document-plugin/issues/new?title=${title}&body=${body}`,
      '_blank'
    )
  }

  return (
    <div className="flex h-screen w-full items-center justify-center overflow-auto bg-red-50 p-5">
      <div className="w-full text-center">
        <div className="inline-flex rounded-full bg-red-100 p-4">
          <div className="rounded-full bg-red-200 stroke-red-600 p-4">
            <svg
              className="h-16 w-16"
              viewBox="0 0 28 28"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M6 8H6.01M6 16H6.01M6 12H18C20.2091 12 22 10.2091 22 8C22 5.79086 20.2091 4 18 4H6C3.79086 4 2 5.79086 2 8C2 10.2091 3.79086 12 6 12ZM6 12C3.79086 12 2 13.7909 2 16C2 18.2091 3.79086 20 6 20H14"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              ></path>
              <path
                d="M17 16L22 21M22 16L17 21"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              ></path>
            </svg>
          </div>
        </div>
        <h1 className="mt-5 text-xl font-bold text-slate-800">
          Oops! Something went wrong.
        </h1>
        <p className="lg:text-md my-2 text-slate-600">
          Try to{' '}
          <button
            className="text-accent hover:underline cursor-pointer"
            onClick={() => window.location.reload()}
          >
            refresh this page
          </button>
          {' '}or report this bug so we can fix it.
        </p>
        <button
          onClick={handleReportBug}
          className="mt-3 inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors cursor-pointer"
        >
          <svg className="h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" />
          </svg>
          Report Bug on GitHub
        </button>
        <div
          className="mt-5 w-full md:w-4/5 mx-auto rounded border border-red-400 bg-red-100 px-4 py-3 text-red-700"
          role="alert"
        >
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">
            {errorMessage}
          </span>
          <div className="mt-2 h-full w-full">
            <pre className="mt-2 whitespace-pre-wrap break-all rounded bg-red-200 p-4 text-left text-sm text-red-600 max-h-[250px] overflow-y-auto">
              <code>
                {error instanceof Error
                  ? showFull
                    ? error.stack
                    : error.stack?.slice(0, 200)
                  : String(error)}
              </code>
            </pre>
            <button
              onClick={() => setShowFull(!showFull)}
              className="mt-2 text-sm text-red-700 underline focus:outline-none cursor-pointer"
            >
              {showFull ? 'Show less' : 'Show more'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
