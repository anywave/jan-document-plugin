import { createFileRoute } from '@tanstack/react-router'
import { route } from '@/constants/routes'
import HeaderPage from '@/containers/HeaderPage'
import { DocumentRAG } from '@/extensions/document-rag/src/components/DocumentRAG'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const Route = createFileRoute(route.documents as any)({
  component: Documents,
})

function Documents() {
  return (
    <div className="flex h-full flex-col flex-justify-center">
      <HeaderPage>
        <span>Documents</span>
      </HeaderPage>
      <div className="h-full p-4 overflow-y-auto">
        <DocumentRAG defaultTab="upload" />
      </div>
    </div>
  )
}
