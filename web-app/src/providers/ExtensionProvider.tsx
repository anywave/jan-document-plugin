import { ExtensionManager } from '@/lib/extension'
import { APIs } from '@/lib/service'
import { EventEmitter } from '@/services/events'
import { EngineManager, ModelManager } from '@janhq/core'
import { PropsWithChildren, useCallback, useEffect, useState } from 'react'

export function ExtensionProvider({ children }: PropsWithChildren) {
  const [finishedSetup, setFinishedSetup] = useState(false)
  const setupExtensions = useCallback(async () => {
    window.core = {
      api: APIs,
    }

    window.core.events = new EventEmitter()
    window.core.extensionManager = new ExtensionManager()
    window.core.engineManager = new EngineManager()
    window.core.modelManager = new ModelManager()

    // Register all active extensions
    await ExtensionManager.getInstance()
      .registerActive()
      .then(() => ExtensionManager.getInstance().load())
      .then(() => setFinishedSetup(true))
      .catch((err) => {
        console.error('Extension loading failed:', err)
        setFinishedSetup(true) // Show app UI even if extensions fail
      })
  }, [])

  useEffect(() => {
    setupExtensions()

    return () => {
      ExtensionManager.getInstance().unload()
    }
  }, [setupExtensions])

  return <>{finishedSetup && children}</>
}
