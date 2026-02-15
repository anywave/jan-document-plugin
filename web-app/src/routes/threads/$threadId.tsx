import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createFileRoute, useParams } from '@tanstack/react-router'
import { UIEventHandler } from 'react'
import debounce from 'lodash.debounce'
import cloneDeep from 'lodash.clonedeep'
import { cn } from '@/lib/utils'
import { ArrowDown, Play } from 'lucide-react'
import { toast } from 'sonner'

import HeaderPage from '@/containers/HeaderPage'
import { useThreads } from '@/hooks/useThreads'
import ChatInput from '@/containers/ChatInput'
import { useShallow } from 'zustand/react/shallow'
import { ThreadContent } from '@/containers/ThreadContent'
import { StreamingContent } from '@/containers/StreamingContent'

import { useMessages } from '@/hooks/useMessages'
import { fetchMessages } from '@/services/messages'
import { useAppState } from '@/hooks/useAppState'
import DropdownAssistant from '@/containers/DropdownAssistant'
import { useAssistant } from '@/hooks/useAssistant'
import { useAppearance } from '@/hooks/useAppearance'
import { ContentType, ThreadMessage } from '@janhq/core'
import { useTranslation } from '@/i18n/react-i18next-compat'
import { useChat } from '@/hooks/useChat'
import { useSmallScreen } from '@/hooks/useMediaQuery'
import { usePrompt } from '@/hooks/usePrompt'
import { useModelProvider } from '@/hooks/useModelProvider'
import { useChatExcerpts } from '@/hooks/useChatExcerpts'
import { useTextSelection } from '@/hooks/useTextSelection'
import { sendCompletion, isCompletionResponse } from '@/lib/completion'
import { SelectionContextMenu } from '@/components/SelectionContextMenu'
import { AnnotationCard } from '@/components/AnnotationCard'
import { useTTS } from '@/hooks/useTTS'
import { TTSControls } from '@/components/TTSControls'
import { VoiceAssignmentDialog } from '@/components/VoiceAssignmentDialog'

// as route.threadsDetail
export const Route = createFileRoute('/threads/$threadId')({
  component: ThreadDetail,
})

function ThreadDetail() {
  const { t } = useTranslation()
  const { threadId } = useParams({ from: Route.id })
  const [isUserScrolling, setIsUserScrolling] = useState(false)
  const [isAtBottom, setIsAtBottom] = useState(true)
  const [hasScrollbar, setHasScrollbar] = useState(false)
  const lastScrollTopRef = useRef(0)
  const { currentThreadId, setCurrentThreadId } = useThreads()
  const { setCurrentAssistant, assistants } = useAssistant()
  const { setMessages, deleteMessage } = useMessages()
  const { streamingContent } = useAppState()
  const { appMainViewBgColor, chatWidth } = useAppearance()
  const { sendMessage } = useChat()
  const isSmallScreen = useSmallScreen()
  const { setPrompt } = usePrompt()
  const { getProviderByName } = useModelProvider()
  const { addExcerpt, addAnnotation, removeAnnotation } = useChatExcerpts()
  const ttsPlay = useTTS((s) => s.play)

  const { messages } = useMessages(
    useShallow((state) => ({
      messages: state.messages[threadId],
    }))
  )

  // Subscribe directly to the thread data to ensure updates when model changes
  const thread = useThreads(useShallow((state) => state.threads[threadId]))
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const isFirstRender = useRef(true)
  const messagesCount = useMemo(() => messages?.length ?? 0, [messages])

  // Text selection context menu
  const { selection, clearSelection } = useTextSelection(scrollContainerRef)

  // Annotations for this thread
  const threadAnnotations = useChatExcerpts(
    useShallow((s) => s.annotations.filter((a) => a.threadId === threadId))
  )
  const annotationsMap = useMemo(
    () => new Map(threadAnnotations.map((a) => [a.messageId, a])),
    [threadAnnotations]
  )

  // Helper: find the input prompt (most recent user message before target)
  const findInputPrompt = useCallback(
    (targetIndex: number): string | null => {
      if (!messages) return null
      for (let i = targetIndex - 1; i >= 0; i--) {
        if (messages[i].role === 'user') {
          return messages[i].content?.[0]?.text?.value ?? null
        }
      }
      return null
    },
    [messages]
  )

  // Handler: Send selected text to chat input
  const handleSendToChat = useCallback(() => {
    if (!selection) return
    setPrompt(selection.selectedText)
    clearSelection()
  }, [selection, setPrompt, clearSelection])

  // Handler: Save selected text to Xtract Library
  const handleSaveToXtractLib = useCallback(() => {
    if (!selection || !messages) return
    const msg = messages.find((m) => m.id === selection.messageId)
    if (!msg) return

    const fullMessage = msg.content
      ?.map((c) => c.text?.value ?? '')
      .filter(Boolean)
      .join('\n') ?? ''

    const assistantName = thread?.assistants?.[0]?.name || thread?.assistants?.[0]?.id || 'Assistant'

    addExcerpt({
      threadId,
      messageId: selection.messageId,
      highlightText: selection.selectedText,
      fullMessage,
      assistantName,
      timestamp: msg.created_at ?? Date.now(),
      inputPrompt: findInputPrompt(selection.messageIndex),
    })
    toast.success('Saved to Xtract Library')
    clearSelection()
  }, [selection, messages, thread, threadId, addExcerpt, findInputPrompt, clearSelection])

  // Handler: Summarize selected text via LLM
  const handleSummarize = useCallback(async () => {
    if (!selection || !thread?.model) return

    const providerName = thread.model.provider
    if (!providerName) {
      toast.error('No model provider configured')
      return
    }
    const provider = getProviderByName(providerName)
    if (!provider) {
      toast.error('Model provider not found')
      return
    }

    const toastId = toast.loading('Summarizing...')
    const abort = new AbortController()

    try {
      const result = await sendCompletion(
        thread,
        provider,
        [
          { role: 'system', content: 'Summarize the following text in 2-3 concise sentences. Focus on key points.' },
          { role: 'user', content: selection.selectedText },
        ],
        abort,
        [],
        false
      )

      if (result && isCompletionResponse(result)) {
        const choices = (result as { choices: { message: { content: string } }[] }).choices
        const summary = choices[0]?.message?.content ?? ''
        if (summary) {
          addAnnotation({
            threadId,
            messageId: selection.messageId,
            sourceText: selection.selectedText,
            summary,
          })
          toast.success('Summary added', { id: toastId })
        } else {
          toast.error('Empty summary response', { id: toastId })
        }
      } else {
        toast.error('Summarization failed', { id: toastId })
      }
    } catch (err) {
      console.error('Summarize error:', err)
      toast.error('Summarization failed — model may be offline', { id: toastId })
    }
    clearSelection()
  }, [selection, thread, threadId, getProviderByName, addAnnotation, clearSelection])

  // Handler: Read Aloud selected text via TTS
  const handleReadAloud = useCallback(() => {
    if (!selection) return
    const threadTitle = thread?.title || undefined
    ttsPlay(selection.selectedText, threadTitle).catch(() => {
      toast.error('Failed to generate speech')
    })
    clearSelection()
  }, [selection, thread, ttsPlay, clearSelection])

  // Function to check scroll position and scrollbar presence
  const checkScrollState = () => {
    const scrollContainer = scrollContainerRef.current
    if (!scrollContainer) return

    const { scrollTop, scrollHeight, clientHeight } = scrollContainer
    const isBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 10
    const hasScroll = scrollHeight > clientHeight

    setIsAtBottom(isBottom)
    setHasScrollbar(hasScroll)
  }

  useEffect(() => {
    if (currentThreadId !== threadId) {
      setCurrentThreadId(threadId)
      const assistant = assistants.find(
        (assistant) => assistant.id === thread?.assistants?.[0]?.id
      )
      if (assistant) setCurrentAssistant(assistant)
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId, currentThreadId, assistants])

  useEffect(() => {
    fetchMessages(threadId).then((fetchedMessages) => {
      if (fetchedMessages) {
        // Update the messages in the store
        setMessages(threadId, fetchedMessages)
      }
    }).catch((err) => console.error(`Failed to fetch messages for ${threadId}:`, err))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId])

  useEffect(() => {
    return () => {
      // Clear the current thread ID when the component unmounts
      setCurrentThreadId(undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-scroll to bottom when component mounts or thread content changes
  useEffect(() => {
    const scrollContainer = scrollContainerRef.current
    if (!scrollContainer) return

    // Always scroll to bottom on first render or when thread changes
    if (isFirstRender.current) {
      isFirstRender.current = false
      scrollToBottom()
      setIsAtBottom(true)
      setIsUserScrolling(false)
      checkScrollState()
      return
    }
  }, [])

  // Reset scroll state when thread changes
  useEffect(() => {
    isFirstRender.current = true
    scrollToBottom()
    setIsAtBottom(true)
    setIsUserScrolling(false)
    checkScrollState()
  }, [threadId])

  // Single useEffect for all auto-scrolling logic
  useEffect(() => {
    // Only auto-scroll when the user is not actively scrolling
    // AND either at the bottom OR there's streaming content
    if (!isUserScrolling && (streamingContent || isAtBottom) && messagesCount) {
      // Use non-smooth scrolling for auto-scroll to prevent jank
      scrollToBottom(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [streamingContent, isUserScrolling, messagesCount])

  useEffect(() => {
    if (streamingContent) {
      const interval = setInterval(checkScrollState, 100)
      return () => clearInterval(interval)
    }
  }, [streamingContent])

  const scrollToBottom = (smooth = false) => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        ...(smooth ? { behavior: 'smooth' } : {}),
      })
    }
  }

  const handleScroll: UIEventHandler<HTMLDivElement> = (e) => {
    const target = e.target as HTMLDivElement
    const { scrollTop, scrollHeight, clientHeight } = target
    // Use a small tolerance to better detect when we're at the bottom
    const isBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 10
    const hasScroll = scrollHeight > clientHeight

    // Detect if this is a user-initiated scroll
    if (Math.abs(scrollTop - lastScrollTopRef.current) > 10) {
      setIsUserScrolling(!isBottom)
    }
    setIsAtBottom(isBottom)
    setHasScrollbar(hasScroll)
    lastScrollTopRef.current = scrollTop
  }

  // Separate handler for DOM events
  const handleDOMScroll = (e: Event) => {
    const target = e.target as HTMLDivElement
    const { scrollTop, scrollHeight, clientHeight } = target
    // Use a small tolerance to better detect when we're at the bottom
    const isBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 10
    const hasScroll = scrollHeight > clientHeight

    // Detect if this is a user-initiated scroll
    if (Math.abs(scrollTop - lastScrollTopRef.current) > 10) {
      setIsUserScrolling(!isBottom)
    }
    setIsAtBottom(isBottom)
    setHasScrollbar(hasScroll)
    lastScrollTopRef.current = scrollTop
  }

  const updateMessage = (item: ThreadMessage, message: string) => {
    const newMessages: ThreadMessage[] = messages.map((m) => {
      if (m.id === item.id) {
        const msg: ThreadMessage = cloneDeep(m)
        msg.content = [
          {
            type: ContentType.Text,
            text: {
              value: message,
              annotations: m.content[0].text?.annotations ?? [],
            },
          },
        ]
        return msg
      }
      return m
    })
    setMessages(threadId, newMessages)
  }

  // Use a shorter debounce time for more responsive scrolling
  const debouncedScroll = debounce(handleDOMScroll)

  useEffect(() => {
    const chatHistoryElement = scrollContainerRef.current
    if (chatHistoryElement) {
      chatHistoryElement.addEventListener('scroll', debouncedScroll)
      return () =>
        chatHistoryElement.removeEventListener('scroll', debouncedScroll)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // used when there is a sent/added user message and no assistant message (error or manual deletion)
  const generateAIResponse = () => {
    const latestUserMessage = messages[messages.length - 1]
    if (
      latestUserMessage?.content?.[0]?.text?.value &&
      latestUserMessage.role === 'user'
    ) {
      sendMessage(latestUserMessage.content[0].text.value, false)
    } else if (latestUserMessage?.metadata?.tool_calls) {
      // Only regenerate assistant message is allowed
      const threadMessages = [...messages]
      let toSendMessage = threadMessages.pop()
      while (toSendMessage && toSendMessage?.role !== 'user') {
        deleteMessage(toSendMessage.thread_id, toSendMessage.id ?? '')
        toSendMessage = threadMessages.pop()
      }
      if (toSendMessage) {
        deleteMessage(toSendMessage.thread_id, toSendMessage.id ?? '')
        sendMessage(toSendMessage.content?.[0]?.text?.value || '')
      }
    }
  }

  const threadModel = useMemo(() => thread?.model, [thread])

  if (!messages || !threadModel) return null

  const showScrollToBottomBtn = !isAtBottom && hasScrollbar
  const showGenerateAIResponseBtn =
    (messages[messages.length - 1]?.role === 'user' ||
      (messages[messages.length - 1]?.metadata &&
        'tool_calls' in (messages[messages.length - 1].metadata ?? {}))) &&
    !streamingContent

  return (
    <div className="flex flex-col h-full">
      <HeaderPage>
        <div className="flex items-center justify-between w-full pr-2">
          <DropdownAssistant />
        </div>
      </HeaderPage>
      <div className="flex flex-col h-[calc(100%-40px)] ">
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className={cn(
            'flex flex-col h-full w-full overflow-auto px-4 pt-4 pb-3'
          )}
        >
          <div
            className={cn(
              'w-4/6 mx-auto flex max-w-full flex-col grow',
              chatWidth === 'compact' ? 'w-full md:w-4/6' : 'w-full',
              isSmallScreen && 'w-full'
            )}
          >
            {messages &&
              messages.map((item, index) => {
                // Only pass isLastMessage to the last message in the array
                const isLastMessage = index === messages.length - 1
                const annotation = annotationsMap.get(item.id)
                return (
                  <div
                    key={item.id}
                    data-test-id={`message-${item.role}-${item.id}`}
                    data-message-author-role={item.role}
                    data-message-id={item.id}
                    data-message-index={index}
                    className="mb-4 relative group/msg"
                  >
                    {annotation && (
                      <div className="absolute right-full top-0 mr-3 w-48 hidden lg:block">
                        <div className="absolute top-4 -right-3 w-3 h-px bg-main-view-fg/20" />
                        <AnnotationCard
                          annotation={annotation}
                          onRemove={removeAnnotation}
                        />
                      </div>
                    )}
                    <ThreadContent
                      {...item}
                      isLastMessage={isLastMessage}
                      showAssistant={
                        item.role === 'assistant' &&
                        (index === 0 ||
                          messages[index - 1]?.role !== 'assistant' ||
                          !(
                            messages[index - 1]?.metadata &&
                            'tool_calls' in (messages[index - 1].metadata ?? {})
                          ))
                      }
                      index={index}
                      updateMessage={updateMessage}
                    />
                    {item.role === 'assistant' && item.content?.[0]?.text?.value && (
                      <div className="flex justify-end mt-1 mr-2 opacity-0 hover:opacity-100 transition-opacity group-hover/msg:opacity-60">
                        <TTSControls
                          text={item.content.map((c) => c.text?.value ?? '').filter(Boolean).join('\n')}
                          threadTitle={thread?.title}
                        />
                      </div>
                    )}
                  </div>
                )
              })}
            <StreamingContent
              threadId={threadId}
              data-test-id="thread-content-text"
            />
          </div>
        </div>
        <div
          className={cn(
            'mx-auto pt-2 pb-3 shrink-0 relative px-2',
            chatWidth === 'compact' ? 'w-full md:w-4/6' : 'w-full',
            isSmallScreen && 'w-full'
          )}
        >
          <div
            className={cn(
              'absolute z-0 -top-6 h-8 py-1 flex w-full justify-center pointer-events-none opacity-0 visibility-hidden',
              appMainViewBgColor.a === 1
                ? 'from-main-view/20 bg-gradient-to-b to-main-view backdrop-blur'
                : 'bg-transparent',
              (showScrollToBottomBtn || showGenerateAIResponseBtn) &&
                'visibility-visible opacity-100'
            )}
          >
            {showScrollToBottomBtn && (
              <div
                className="bg-main-view-fg/10 px-2 border border-main-view-fg/5 flex items-center justify-center rounded-xl gap-x-2 cursor-pointer pointer-events-auto"
                onClick={() => {
                  scrollToBottom(true)
                  setIsUserScrolling(false)
                }}
              >
                <p className="text-xs">{t('scrollToBottom')}</p>
                <ArrowDown size={12} />
              </div>
            )}
            {showGenerateAIResponseBtn && (
              <div
                className="mx-2 bg-main-view-fg/10 px-2 border border-main-view-fg/5 flex items-center justify-center rounded-xl gap-x-2 cursor-pointer pointer-events-auto"
                onClick={generateAIResponse}
              >
                <p className="text-xs">{t('common:generateAiResponse')}</p>
                <Play size={12} />
              </div>
            )}
          </div>
          <ChatInput model={threadModel} />
        </div>
      </div>
      {selection && (
        <SelectionContextMenu
          selection={selection}
          onSendToChat={handleSendToChat}
          onSaveToXtractLib={handleSaveToXtractLib}
          onSummarize={handleSummarize}
          onReadAloud={handleReadAloud}
          onClose={clearSelection}
        />
      )}
      <VoiceAssignmentDialog />
    </div>
  )
}
