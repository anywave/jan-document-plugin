/**
 * MOBIUS Lock Status Hook
 * Checks Jan lock status from Windows registry and provides it to settings components.
 */

import { create } from 'zustand'
import { invoke } from '@tauri-apps/api/core'

interface JanLockStatus {
  jan_installed: boolean
  jan_version: string | null
  jan_install_path: string | null
  mobius_locked: boolean
}

interface LockStatusState {
  lockStatus: JanLockStatus | null
  loading: boolean
  fetchLockStatus: () => Promise<void>
}

export const useLockStatus = create<LockStatusState>((set) => ({
  lockStatus: null,
  loading: false,

  fetchLockStatus: async () => {
    set({ loading: true })
    try {
      const status = await invoke<JanLockStatus>('check_jan_lock_status')
      set({ lockStatus: status, loading: false })
    } catch (error) {
      console.warn('[MOBIUS] Failed to check lock status:', error)
      set({
        lockStatus: {
          jan_installed: false,
          jan_version: null,
          jan_install_path: null,
          mobius_locked: false,
        },
        loading: false,
      })
    }
  },
}))
