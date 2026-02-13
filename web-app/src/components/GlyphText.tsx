import { memo, useMemo } from 'react'
import { GLYPH_CHARS } from '@/hooks/useTTS'

interface GlyphTextProps {
  text: string
  singing?: boolean
}

/**
 * Renders text with glyph characters wrapped in shimmer-animated spans.
 * When `singing` is true (TTS active), glyphs get the intensified animation.
 */
export const GlyphText = memo(({ text, singing = false }: GlyphTextProps) => {
  const parts = useMemo(() => {
    const result: { text: string; isGlyph: boolean }[] = []
    let current = ''

    for (const ch of text) {
      if (GLYPH_CHARS.has(ch)) {
        if (current) {
          result.push({ text: current, isGlyph: false })
          current = ''
        }
        result.push({ text: ch, isGlyph: true })
      } else {
        current += ch
      }
    }
    if (current) {
      result.push({ text: current, isGlyph: false })
    }
    return result
  }, [text])

  // If no glyphs, just return plain text
  if (parts.length === 1 && !parts[0].isGlyph) {
    return <>{text}</>
  }

  return (
    <>
      {parts.map((part, i) =>
        part.isGlyph ? (
          <span
            key={i}
            className={`glyph-char${singing ? ' singing' : ''}`}
          >
            {part.text}
          </span>
        ) : (
          <span key={i}>{part.text}</span>
        )
      )}
    </>
  )
})
