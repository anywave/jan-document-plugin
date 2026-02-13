import {
  DndContext,
  closestCenter,
  useSensor,
  useSensors,
  PointerSensor,
  KeyboardSensor,
} from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  IconDots,
  IconStarFilled,
  IconTrash,
  IconEdit,
  IconStar,
  IconSquare,
  IconSquareCheckFilled,
  IconArchive,
  IconShare,
} from '@tabler/icons-react'
import { useThreads } from '@/hooks/useThreads'
import { useLeftPanel } from '@/hooks/useLeftPanel'
import { cn } from '@/lib/utils'
import { route } from '@/constants/routes'
import { useSmallScreen } from '@/hooks/useMediaQuery'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useTranslation } from '@/i18n/react-i18next-compat'
import { DialogClose, DialogFooter, DialogHeader } from '@/components/ui/dialog'
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { memo, useMemo, useState } from 'react'
import { useNavigate, useMatches } from '@tanstack/react-router'
import { toast } from 'sonner'
import { Input } from '@/components/ui/input'

type SortableItemProps = {
  thread: Thread
  selectMode?: boolean
  isSelected?: boolean
  selectedIds?: Set<string>
  onToggleSelect?: (id: string) => void
  orderedThreadIds: string[]
}

const SortableItem = memo(({
  thread,
  selectMode,
  isSelected,
  selectedIds,
  onToggleSelect,
  orderedThreadIds,
}: SortableItemProps) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: thread.id, disabled: true })

  const isSmallScreen = useSmallScreen()
  const { setLeftPanel } = useLeftPanel()

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }
  const {
    toggleFavorite, deleteThread, renameThread,
    lastSelectedId, selectRange, setSelectMode,
    archiveSelected, deleteSelected, clearSelection,
  } = useThreads()
  const { t } = useTranslation()
  const [openDropdown, setOpenDropdown] = useState(false)
  const [showBulkMenu, setShowBulkMenu] = useState(false)
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false)
  const navigate = useNavigate()
  // Check if current route matches this thread's detail page
  const matches = useMatches()
  const isActive = matches.some(
    (match) =>
      match.routeId === '/threads/$threadId' &&
      'threadId' in match.params &&
      match.params.threadId === thread.id
  )

  const handleClick = (e: React.MouseEvent) => {
    if (e.shiftKey && lastSelectedId) {
      e.preventDefault()
      selectRange(lastSelectedId, thread.id, orderedThreadIds)
      return
    }
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault()
      if (!selectMode) setSelectMode(true)
      onToggleSelect?.(thread.id)
      return
    }
    if (selectMode) {
      onToggleSelect?.(thread.id)
      return
    }
    if (!isDragging && !isActive) {
      if (isSmallScreen) setLeftPanel(false)
      navigate({ to: route.threadsDetail, params: { threadId: thread.id } })
    }
  }

  const plainTitleForRename = useMemo(() => {
    return (thread.title || '').replace(/<span[^>]*>|<\/span>/g, '')
  }, [thread.title])

  const [title, setTitle] = useState(
    plainTitleForRename || t('common:newThread')
  )

  const bulkCount = selectedIds?.size ?? 0

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={handleClick}
      onContextMenu={(e) => {
        e.preventDefault()
        e.stopPropagation()
        // If right-clicking a selected thread in multi-select, show bulk menu
        if (selectedIds && selectedIds.has(thread.id) && selectedIds.size > 1) {
          setShowBulkMenu(true)
        } else {
          // Clear selection if right-clicking an unselected thread while in select mode
          if (selectMode && selectedIds && !selectedIds.has(thread.id)) {
            clearSelection()
            setSelectMode(false)
          }
          setOpenDropdown(true)
        }
      }}
      className={cn(
        'mb-1 rounded hover:bg-left-panel-fg/10 flex items-center justify-between gap-2 px-1.5 group/thread-list transition-all',
        isDragging ? 'cursor-move' : 'cursor-pointer',
        isActive && !selectMode && 'bg-left-panel-fg/10',
        selectMode && isSelected && 'bg-left-panel-fg/15'
      )}
    >
      <div className="py-1 pr-2 truncate flex items-center gap-1.5">
        {selectMode && (
          isSelected
            ? <IconSquareCheckFilled size={16} className="text-left-panel-fg shrink-0" />
            : <IconSquare size={16} className="text-left-panel-fg/40 shrink-0" />
        )}
        <span className="truncate">{thread.title || t('common:newThread')}</span>
      </div>

      {/* Bulk context menu for multi-select right-click */}
      <DropdownMenu
        open={showBulkMenu}
        onOpenChange={(open) => setShowBulkMenu(open)}
      >
        <DropdownMenuTrigger asChild>
          <span className="sr-only">Bulk actions</span>
        </DropdownMenuTrigger>
        <DropdownMenuContent side="bottom" align="end">
          <Dialog open={bulkDeleteConfirm} onOpenChange={setBulkDeleteConfirm}>
            <DialogTrigger asChild>
              <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                <IconTrash />
                <span>Delete {bulkCount} thread{bulkCount !== 1 ? 's' : ''}</span>
              </DropdownMenuItem>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete {bulkCount} thread{bulkCount !== 1 ? 's' : ''}?</DialogTitle>
                <DialogDescription>
                  This action cannot be undone. The selected threads and all their messages will be permanently deleted.
                </DialogDescription>
                <DialogFooter className="mt-2">
                  <DialogClose asChild>
                    <Button variant="link" size="sm" className="hover:no-underline">
                      {t('common:cancel')}
                    </Button>
                  </DialogClose>
                  <Button
                    variant="destructive"
                    onClick={() => {
                      deleteSelected()
                      setBulkDeleteConfirm(false)
                      setShowBulkMenu(false)
                      toast.success(`${bulkCount} thread${bulkCount !== 1 ? 's' : ''} deleted`, {
                        id: 'delete-selected',
                      })
                      setTimeout(() => navigate({ to: route.home }), 0)
                    }}
                  >
                    {t('common:delete')}
                  </Button>
                </DialogFooter>
              </DialogHeader>
            </DialogContent>
          </Dialog>
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              archiveSelected()
              setShowBulkMenu(false)
              toast.success(`${bulkCount} thread${bulkCount !== 1 ? 's' : ''} archived`, {
                id: 'archive-selected',
              })
            }}
          >
            <IconArchive />
            <span>Archive {bulkCount} thread{bulkCount !== 1 ? 's' : ''}</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Single-thread context menu */}
      {!selectMode && <div className="flex items-center">
        <DropdownMenu
          open={openDropdown}
          onOpenChange={(open) => setOpenDropdown(open)}
        >
          <DropdownMenuTrigger asChild>
            <IconDots
              size={14}
              className="text-left-panel-fg/60 shrink-0 cursor-pointer px-0.5 -mr-1 data-[state=open]:bg-left-panel-fg/10 rounded group-hover/thread-list:data-[state=closed]:size-5 size-5 data-[state=closed]:size-0"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
              }}
            />
          </DropdownMenuTrigger>
          <DropdownMenuContent side="bottom" align="end">
            {thread.isFavorite ? (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  toggleFavorite(thread.id)
                }}
              >
                <IconStarFilled />
                <span>{t('common:unstar')}</span>
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  toggleFavorite(thread.id)
                }}
              >
                <IconStar />
                <span>{t('common:star')}</span>
              </DropdownMenuItem>
            )}
            <Dialog
              onOpenChange={(open) => {
                if (open) {
                  setTitle(plainTitleForRename || t('common:newThread'))
                } else {
                  setOpenDropdown(false)
                }
              }}
            >
              <DialogTrigger asChild>
                <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                  <IconEdit />
                  <span>{t('common:rename')}</span>
                </DropdownMenuItem>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{t('common:threadTitle')}</DialogTitle>
                  <Input
                    value={title}
                    onChange={(e) => {
                      setTitle(e.target.value)
                    }}
                    className="mt-2"
                    onKeyDown={(e) => {
                      e.stopPropagation()
                    }}
                  />
                  <DialogFooter className="mt-2 flex items-center">
                    <DialogClose asChild>
                      <Button
                        variant="link"
                        size="sm"
                        className="hover:no-underline"
                      >
                        {t('common:cancel')}
                      </Button>
                    </DialogClose>
                    <Button
                      disabled={!title}
                      onClick={() => {
                        renameThread(thread.id, title)
                        setOpenDropdown(false)
                        toast.success(t('common:toast.renameThread.title'), {
                          id: 'rename-thread',
                          description: t(
                            'common:toast.renameThread.description',
                            { title }
                          ),
                        })
                      }}
                    >
                      {t('common:rename')}
                    </Button>
                  </DialogFooter>
                </DialogHeader>
              </DialogContent>
            </Dialog>

            <DropdownMenuSeparator />
            <Dialog
              onOpenChange={(open) => {
                if (!open) setOpenDropdown(false)
              }}
            >
              <DialogTrigger asChild>
                <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                  <IconTrash />
                  <span>{t('common:delete')}</span>
                </DropdownMenuItem>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{t('common:deleteThread')}</DialogTitle>
                  <DialogDescription>
                    {t('common:dialogs.deleteThread.description')}
                  </DialogDescription>
                  <DialogFooter className="mt-2 flex items-center">
                    <DialogClose asChild>
                      <Button
                        variant="link"
                        size="sm"
                        className="hover:no-underline"
                      >
                        {t('common:cancel')}
                      </Button>
                    </DialogClose>
                    <Button
                      variant="destructive"
                      onClick={() => {
                        deleteThread(thread.id)
                        setOpenDropdown(false)
                        toast.success(t('common:toast.deleteThread.title'), {
                          id: 'delete-thread',
                          description: t(
                            'common:toast.deleteThread.description'
                          ),
                        })
                        setTimeout(() => {
                          navigate({ to: route.home })
                        }, 0)
                      }}
                    >
                      {t('common:delete')}
                    </Button>
                  </DialogFooter>
                </DialogHeader>
              </DialogContent>
            </Dialog>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>}
    </div>
  )
})

type ThreadListProps = {
  threads: Thread[]
  isFavoriteSection?: boolean
  selectMode?: boolean
  selectedIds?: Set<string>
  onToggleSelect?: (id: string) => void
}

function ThreadList({ threads, selectMode, selectedIds, onToggleSelect }: ThreadListProps) {
  const sortedThreads = useMemo(() => {
    return threads.sort((a, b) => {
      return (b.updated || 0) - (a.updated || 0)
    })
  }, [threads])

  const orderedThreadIds = useMemo(() => {
    return sortedThreads.map((t) => t.id)
  }, [sortedThreads])

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        delay: 200,
        tolerance: 5,
      },
    }),
    useSensor(KeyboardSensor)
  )

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter}>
      <SortableContext
        items={sortedThreads.map((t) => t.id)}
        strategy={verticalListSortingStrategy}
      >
        {sortedThreads.map((thread, index) => (
          <SortableItem
            key={index}
            thread={thread}
            selectMode={selectMode}
            isSelected={selectedIds?.has(thread.id)}
            selectedIds={selectedIds}
            onToggleSelect={onToggleSelect}
            orderedThreadIds={orderedThreadIds}
          />
        ))}
      </SortableContext>
    </DndContext>
  )
}

export default memo(ThreadList)
