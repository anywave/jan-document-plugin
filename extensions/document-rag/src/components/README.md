# Document RAG UI Components

React components for MOBIUS's document RAG functionality.

## Components

### DocumentRAG (Main Container)

The main component that integrates all functionality with tabs.

```tsx
import { DocumentRAG } from './components'

function App() {
  return (
    <DocumentRAG
      defaultTab="upload"
      collectionName="documents"
    />
  )
}
```

**Props**:
- `defaultTab`: 'upload' | 'library' | 'search' (default: 'upload')
- `collectionName`: string (default: 'documents')
- `className`: string

**Features**:
- Tab navigation (Upload, Library, Search)
- Python environment check on mount
- Error states for missing Python
- Status badge showing Python version

---

### DocumentUpload

File upload component with drag & drop support.

```tsx
import { DocumentUpload } from './components'

<DocumentUpload
  collectionName="documents"
  onUploadComplete={(filePath, chunks) => {
    console.log(`Uploaded ${filePath} with ${chunks} chunks`)
  }}
/>
```

**Props**:
- `collectionName`: string (default: 'documents')
- `onUploadComplete`: (filePath: string, chunks: number) => void
- `className`: string

**Features**:
- Drag & drop file upload
- Multi-file selection
- File type validation
- Real-time processing progress
- Progress indicators for each file
- Error handling with user feedback

**Supported Formats**:
- PDF (.pdf)
- Word (.docx, .doc)
- Text (.txt, .md)
- Images (.png, .jpg, .jpeg, .bmp, .tiff, .tif)

---

### DocumentLibrary

Grid view of uploaded documents with metadata.

```tsx
import { DocumentLibrary } from './components'

<DocumentLibrary
  collectionName="documents"
  onDocumentSelect={(doc) => {
    console.log('Selected:', doc)
  }}
/>
```

**Props**:
- `collectionName`: string (default: 'documents')
- `onDocumentSelect`: (document: Document) => void
- `className`: string

**Features**:
- Grid layout of document cards
- Document metadata display (name, type, chunks, date)
- File type icons with color coding
- Collection tabs (if multiple collections)
- Search box for filtering
- Empty state UI
- Loading skeletons
- Hover actions (delete)

---

### SearchInterface

Query interface for semantic document search.

```tsx
import { SearchInterface } from './components'

<SearchInterface collectionName="documents" />
```

**Props**:
- `collectionName`: string (default: 'documents')
- `className`: string

**Features**:
- Large search input with placeholder
- Advanced options panel (top-k slider)
- Keyboard shortcuts (Enter to search)
- Loading states
- Clear button
- Search tips
- Results display with QueryResults component

---

### QueryResults

Displays search results with relevance scores.

```tsx
import { QueryResults } from './components'

<QueryResults
  results={queryResult}
  query="machine learning"
/>
```

**Props**:
- `results`: QueryResult (from queryDocuments())
- `query`: string (original search query)
- `className`: string

**Features**:
- Results sorted by relevance
- Similarity score (0-100%)
- Query term highlighting
- Source document info
- Expandable text content
- Copy to clipboard
- Color-coded relevance (green/yellow/orange)
- Empty state for no results

---

## Usage Example

### Complete Integration

```tsx
import React from 'react'
import { DocumentRAG } from '@/extensions/document-rag/src/components'

export function DocumentPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">
          Document Intelligence
        </h1>

        <DocumentRAG
          defaultTab="upload"
          collectionName="my-documents"
        />
      </div>
    </div>
  )
}
```

### Individual Components

```tsx
import {
  DocumentUpload,
  SearchInterface,
  DocumentLibrary
} from '@/extensions/document-rag/src/components'

export function CustomLayout() {
  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Left: Upload */}
      <div>
        <DocumentUpload
          collectionName="docs"
          onUploadComplete={(path, chunks) => {
            console.log(`Uploaded: ${chunks} chunks`)
          }}
        />
      </div>

      {/* Right: Search */}
      <div>
        <SearchInterface collectionName="docs" />
      </div>

      {/* Bottom: Library */}
      <div className="col-span-2">
        <DocumentLibrary
          collectionName="docs"
          onDocumentSelect={(doc) => {
            console.log('Selected:', doc)
          }}
        />
      </div>
    </div>
  )
}
```

---

## Styling

All components use Tailwind CSS and follow MOBIUS's design system:

- **Colors**: Uses semantic color tokens (primary, accent, destructive, etc.)
- **Dark Mode**: Fully supports dark mode via theme classes
- **Icons**: Lucide React icons
- **Notifications**: Sonner toasts for feedback

### Color Tokens Used

```css
- primary: Primary brand color
- primary-fg: Primary foreground (text on primary)
- accent: Accent/secondary background
- bg: Main background
- fg: Main foreground (text)
- border: Border color
- muted-fg: Muted text color
- destructive: Error/danger color
```

---

## Dependencies

### Required

- React 19+
- lucide-react (icons)
- sonner (toasts)
- @tauri-apps/api (IPC)

### Python Backend

All components communicate with the Python backend via:
- `../python-bridge.ts` (TypeScript bindings)
- Tauri IPC commands
- Python subprocess execution

---

## Error Handling

All components handle errors gracefully:

1. **Python Not Available**: Shows setup instructions
2. **Upload Errors**: Toast notifications per file
3. **Search Errors**: Error state in results panel
4. **Network/IPC Errors**: User-friendly error messages

---

## Accessibility

- Keyboard navigation supported
- Focus states on interactive elements
- Semantic HTML structure
- ARIA labels where needed
- Color contrast compliant

---

## Performance

- **Lazy Loading**: Components render on-demand
- **Optimistic UI**: Immediate feedback before async operations
- **Skeleton Loading**: Pleasant loading states
- **Debounced Search**: Prevents excessive queries
- **Memoization**: React optimizations applied

---

## Future Enhancements

- [ ] Document preview modal
- [ ] Batch delete operations
- [ ] Collection management UI
- [ ] Export search results
- [ ] Advanced filtering options
- [ ] Document tagging/categorization
- [ ] Full-text highlighting in results
- [ ] Drag & drop document reordering

---

## Testing

Each component can be tested individually:

```tsx
import { render, screen } from '@testing-library/react'
import { DocumentUpload } from './DocumentUpload'

test('renders upload component', () => {
  render(<DocumentUpload />)
  expect(screen.getByText('Upload Documents')).toBeInTheDocument()
})
```

---

## License

Part of MOBIUS - 100% offline document AI assistant.
