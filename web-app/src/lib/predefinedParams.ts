export type ParamCategory = 'sampling' | 'generation' | 'penalties' | 'advanced'

export interface ParamSetting {
  key: string
  value: unknown
  title: string
  description: string
  friendlyDescription: string
  category: ParamCategory
  advanced: boolean
  min?: number
  max?: number
  step?: number
  compatibility: ('local' | 'openai')[]
  controllerType?: string
}

export const paramCategories: { key: ParamCategory; label: string }[] = [
  { key: 'sampling', label: 'SAMPLING' },
  { key: 'generation', label: 'GENERATION' },
  { key: 'penalties', label: 'PENALTIES' },
  { key: 'advanced', label: 'ADVANCED' },
]

export const paramsSettings: Record<string, ParamSetting> = {
  // ── Sampling ──────────────────────────────────
  temperature: {
    key: 'temperature',
    value: 0.7,
    title: 'Temperature',
    description:
      'Controls response randomness. Higher values produce more creative, varied responses.',
    friendlyDescription:
      'How creative should the AI be? Low = focused and predictable, high = wild and surprising.',
    category: 'sampling',
    advanced: false,
    min: 0,
    max: 2,
    step: 0.1,
    compatibility: ['local', 'openai'],
  },
  top_p: {
    key: 'top_p',
    value: 0.95,
    title: 'Top P',
    description:
      'Set probability threshold for more relevant outputs. Higher values allow more diverse word choices.',
    friendlyDescription:
      'Controls the pool of words the AI picks from. Lower = safer word choices, higher = more variety.',
    category: 'sampling',
    advanced: false,
    min: 0,
    max: 1,
    step: 0.05,
    compatibility: ['local', 'openai'],
    controllerType: 'slider',
  },
  top_k: {
    key: 'top_k',
    value: 40,
    title: 'Top K',
    description:
      'Limits the model to considering only the top K most likely next tokens at each step.',
    friendlyDescription:
      'How many word options does the AI consider at each step? Lower = more focused, higher = more varied.',
    category: 'sampling',
    advanced: false,
    min: 1,
    max: 100,
    step: 1,
    compatibility: ['local'],
  },
  min_p: {
    key: 'min_p',
    value: 0.05,
    title: 'Min P',
    description:
      'Filters out tokens below a minimum probability relative to the most likely token. Adaptive alternative to top_k.',
    friendlyDescription:
      'Automatically filters out unlikely words. A smarter alternative to Top K that adapts to context.',
    category: 'sampling',
    advanced: false,
    min: 0,
    max: 1,
    step: 0.01,
    compatibility: ['local'],
  },
  typical_p: {
    key: 'typical_p',
    value: 1.0,
    title: 'Typical P',
    description:
      'Selects tokens whose cumulative probability of information content is closest to a threshold. Promotes locally typical text.',
    friendlyDescription:
      'Picks words that feel natural in context. Helps avoid both boring and bizarre outputs.',
    category: 'sampling',
    advanced: true,
    min: 0,
    max: 1,
    step: 0.05,
    compatibility: ['local'],
  },
  mirostat: {
    key: 'mirostat',
    value: 0,
    title: 'Mirostat',
    description:
      'Mirostat sampling mode. 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0. Controls perplexity during generation.',
    friendlyDescription:
      'An advanced sampling algorithm that keeps output quality consistent. 0 = off, 1 or 2 = on (try 2).',
    category: 'sampling',
    advanced: true,
    min: 0,
    max: 2,
    step: 1,
    compatibility: ['local'],
  },
  mirostat_tau: {
    key: 'mirostat_tau',
    value: 5.0,
    title: 'Mirostat Tau',
    description:
      'Target entropy (perplexity) for Mirostat. Lower = more focused, higher = more diverse.',
    friendlyDescription:
      'The target "surprise level" for Mirostat. Lower = more predictable, higher = more creative.',
    category: 'sampling',
    advanced: true,
    min: 0,
    max: 10,
    step: 0.1,
    compatibility: ['local'],
  },
  mirostat_eta: {
    key: 'mirostat_eta',
    value: 0.1,
    title: 'Mirostat Eta',
    description:
      'Learning rate for Mirostat feedback. Controls how quickly sampling adapts.',
    friendlyDescription:
      'How fast Mirostat adjusts itself. Usually fine at the default (0.1).',
    category: 'sampling',
    advanced: true,
    min: 0,
    max: 1,
    step: 0.01,
    compatibility: ['local'],
  },

  // ── Generation ────────────────────────────────
  stream: {
    key: 'stream',
    value: true,
    title: 'Stream',
    description: 'Enables real-time response streaming.',
    friendlyDescription:
      'Show words as they appear instead of waiting for the full response. Usually leave this on.',
    category: 'generation',
    advanced: false,
    compatibility: ['local', 'openai'],
  },
  n_predict: {
    key: 'n_predict',
    value: -1,
    title: 'Max Tokens',
    description:
      'Maximum number of tokens to generate. -1 for unlimited (model decides when to stop).',
    friendlyDescription:
      'Maximum length of the response. -1 = let the AI decide when to stop.',
    category: 'generation',
    advanced: false,
    min: -1,
    max: 32768,
    step: 256,
    compatibility: ['local', 'openai'],
  },
  stop: {
    key: 'stop',
    value: [],
    title: 'Stop Sequences',
    description:
      'List of strings that will cause the model to stop generating. Example: ["\\n", "User:"].',
    friendlyDescription:
      'Words or phrases that tell the AI to stop writing. Useful for keeping responses formatted.',
    category: 'generation',
    advanced: false,
    compatibility: ['local', 'openai'],
  },
  seed: {
    key: 'seed',
    value: -1,
    title: 'Seed',
    description:
      'Random seed for reproducibility. -1 for random. Same seed + same prompt = same output.',
    friendlyDescription:
      'Makes responses repeatable. Use the same number to get the same answer twice. -1 = random every time.',
    category: 'generation',
    advanced: false,
    min: -1,
    max: 2147483647,
    step: 1,
    compatibility: ['local', 'openai'],
  },

  // ── Penalties ─────────────────────────────────
  frequency_penalty: {
    key: 'frequency_penalty',
    value: 0,
    title: 'Frequency Penalty',
    description:
      'Reduces word repetition. Higher values encourage more varied language. Useful for creative writing.',
    friendlyDescription:
      'Penalises the AI for repeating the same words too often. Higher = more varied vocabulary.',
    category: 'penalties',
    advanced: false,
    min: -2,
    max: 2,
    step: 0.1,
    compatibility: ['local', 'openai'],
  },
  presence_penalty: {
    key: 'presence_penalty',
    value: 0,
    title: 'Presence Penalty',
    description:
      'Encourages the model to explore new topics. Higher values help prevent fixating on already-discussed subjects.',
    friendlyDescription:
      'Nudges the AI to talk about new things instead of circling back. Higher = explores more topics.',
    category: 'penalties',
    advanced: false,
    min: -2,
    max: 2,
    step: 0.1,
    compatibility: ['local', 'openai'],
  },
  repeat_penalty: {
    key: 'repeat_penalty',
    value: 1.1,
    title: 'Repeat Penalty',
    description:
      'Penalizes recently generated tokens. 1.0 = no penalty. Works on local models alongside frequency/presence penalties.',
    friendlyDescription:
      'Discourages the AI from repeating itself. 1.0 = no effect, 1.1 = mild, 1.3 = strong.',
    category: 'penalties',
    advanced: false,
    min: 0.5,
    max: 2,
    step: 0.05,
    compatibility: ['local'],
  },
  repeat_last_n: {
    key: 'repeat_last_n',
    value: 64,
    title: 'Repeat Last N',
    description:
      'How many recent tokens to consider for repeat penalty. 0 = disabled, -1 = full context.',
    friendlyDescription:
      'How far back the AI checks for repetition. 64 = last ~50 words. -1 = checks everything.',
    category: 'penalties',
    advanced: true,
    min: -1,
    max: 2048,
    step: 16,
    compatibility: ['local'],
  },
  dry_multiplier: {
    key: 'dry_multiplier',
    value: 0,
    title: 'DRY Multiplier',
    description:
      'DRY (Don\'t Repeat Yourself) sampler strength. 0 = disabled. Penalizes repeating n-gram patterns.',
    friendlyDescription:
      'Prevents the AI from repeating phrases or sentence patterns. 0 = off, try 0.8 to start.',
    category: 'penalties',
    advanced: true,
    min: 0,
    max: 5,
    step: 0.1,
    compatibility: ['local'],
  },
  dry_base: {
    key: 'dry_base',
    value: 1.75,
    title: 'DRY Base',
    description:
      'Base of the exponential penalty in DRY sampler. Higher = more aggressive penalty growth.',
    friendlyDescription:
      'How aggressively DRY penalises longer repeated patterns. Default (1.75) is usually fine.',
    category: 'penalties',
    advanced: true,
    min: 1,
    max: 4,
    step: 0.25,
    compatibility: ['local'],
  },
  dry_allowed_length: {
    key: 'dry_allowed_length',
    value: 2,
    title: 'DRY Allowed Length',
    description:
      'Minimum n-gram length before DRY penalty applies. Short common phrases (e.g. "the") are allowed.',
    friendlyDescription:
      'How short a repeated phrase has to be before DRY kicks in. 2 = ignores single repeated words.',
    category: 'penalties',
    advanced: true,
    min: 1,
    max: 8,
    step: 1,
    compatibility: ['local'],
  },

  // ── Advanced ──────────────────────────────────
  logit_bias: {
    key: 'logit_bias',
    value: {},
    title: 'Logit Bias',
    description:
      'JSON object mapping token IDs to bias values (-100 to 100). Directly adjusts token probabilities.',
    friendlyDescription:
      'Manually boost or suppress specific words. For experts — most people can skip this.',
    category: 'advanced',
    advanced: true,
    compatibility: ['local', 'openai'],
  },
}

/**
 * Get params filtered by category, optionally including advanced params.
 */
export function getParamsByCategory(
  category: ParamCategory,
  showAdvanced: boolean
): ParamSetting[] {
  return Object.values(paramsSettings).filter(
    (p) => p.category === category && (showAdvanced || !p.advanced)
  )
}
