export type ParamCategory = 'sampling' | 'generation' | 'penalties' | 'advanced'

export interface ParamSetting {
  key: string
  value: unknown
  title: string
  description: string
  friendlyDescription: string
  technicalDeepDive: string
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
    technicalDeepDive:
      'Temperature scales the logits (raw scores) before the softmax function converts them to probabilities. Each token\'s logit is divided by T before softmax: P(token_i) = exp(logit_i / T) / Σ exp(logit_j / T).\n\nT=0 collapses the distribution to a single peak (greedy decoding — always picks the highest-probability token). T=1 uses the model\'s raw probability distribution as-is. T>1 flattens the distribution, making unlikely tokens relatively more probable.\n\nPractically: T=0.1–0.3 for factual Q&A and code generation. T=0.7 is the general-purpose sweet spot. T=1.0–1.5 for creative writing and brainstorming. Values above 1.5 often produce incoherent output.\n\nTemperature is applied before all other sampling methods (top_p, top_k, min_p). It reshapes the probability landscape that those methods then filter.',
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
    technicalDeepDive:
      'Top P (nucleus sampling) sorts all tokens by probability from highest to lowest, then takes the smallest set whose cumulative probability exceeds the threshold P. Tokens outside this "nucleus" are zeroed out and remaining probabilities are renormalized.\n\nExample: if the top 5 tokens have probabilities [0.40, 0.25, 0.15, 0.10, 0.05, ...] and top_p=0.9, the first 4 tokens (sum=0.90) form the nucleus. The 5th and beyond are discarded.\n\nUnlike top_k (fixed count), top_p adapts to the distribution shape. When the model is confident, fewer tokens pass (tight nucleus). When uncertain, more tokens pass (wide nucleus). This makes it more robust across different contexts.\n\ntop_p=1.0 disables the filter (all tokens pass). top_p=0.1 is extremely restrictive. The standard range is 0.9–0.95. Applied after temperature scaling.',
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
    technicalDeepDive:
      'Top K truncates the probability distribution to only the K most probable tokens, zeroing out all others before renormalization. This is a hard cutoff: exactly K tokens are candidates regardless of their actual probabilities.\n\nK=1 is greedy decoding (always pick the best token). K=40 is the llama.cpp default. K=100 allows significant diversity. Some implementations use K=0 to mean "disabled" (no filtering).\n\nThe limitation of top_k is that it ignores the probability distribution\'s shape. If the model is 99% confident in one token, K=40 still considers 39 near-zero-probability alternatives. Conversely, if probability is spread evenly across 100 tokens, K=40 arbitrarily cuts half of them. This is why min_p and top_p are often preferred — they adapt to the actual distribution.\n\nTop K is applied after temperature. When combined with top_p, both filters run — a token must survive both to be a candidate. Only available for local models (llama.cpp); OpenAI API does not expose this parameter.',
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
    technicalDeepDive:
      'Min P sets a dynamic probability floor relative to the most likely token. A token is kept only if: P(token) >= min_p × P(top_token).\n\nExample: if the top token has probability 0.80 and min_p=0.1, only tokens with probability >= 0.08 survive. If the top token has probability 0.05 (model is uncertain), the threshold drops to 0.005, allowing many more candidates.\n\nThis adaptive behavior is the key advantage over top_k: when the model is confident, very few tokens pass (tight sampling). When uncertain, many tokens pass (broad sampling). The candidate set naturally scales with the distribution\'s entropy.\n\nmin_p=0.05 is a good default. min_p=0.1 is more conservative. min_p=0.01 is very permissive. Proposed by researchers as a simpler, more principled alternative to both top_k and top_p. Only available for local models (llama.cpp).',
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
    technicalDeepDive:
      'Typical P is based on information theory\'s concept of "typical sets." Each token\'s information content (surprisal) is calculated as -log₂ P(token). The expected information content of the distribution is H = -Σ P(token) × log₂ P(token) (the entropy).\n\nTokens are ranked by how close their individual surprisal is to the entropy H. The typical set is the smallest group of tokens — those closest to H — whose cumulative probability exceeds the threshold.\n\nThis filters out two kinds of tokens: (1) very high-probability tokens (too predictable, surprisal << H) and (2) very low-probability tokens (too surprising, surprisal >> H). What remains are tokens that are "typically surprising" — natural-sounding continuations.\n\ntypical_p=1.0 disables the filter. Values of 0.2–0.5 produce noticeably different text from top_p at similar numeric settings. It\'s a niche but powerful tool for improving text naturalness.',
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
    technicalDeepDive:
      'Mirostat is a feedback-based sampling algorithm that dynamically adjusts truncation to maintain a target perplexity (controlled by mirostat_tau). Unlike static methods (top_k, top_p), it adapts in real-time as the model generates text.\n\nThe algorithm maintains an internal variable μ (mu) that controls how many tokens are considered. After each token is sampled, μ is adjusted based on whether the actual surprisal was above or below the target (tau). The learning rate (eta) controls how fast μ adapts.\n\nMode 1 (Mirostat v1): Adjusts top_k dynamically using a Zipf\'s law model of token distributions. Mode 2 (Mirostat v2): Directly adjusts the sampling threshold μ without the Zipf assumption — generally more stable and recommended.\n\nWhen Mirostat is enabled (mode 1 or 2), top_k and top_p are bypassed — Mirostat handles truncation itself. Temperature still applies (it reshapes logits before Mirostat sees them).\n\nThe practical effect: text maintains a consistent "interestingness" level throughout long generations. Without Mirostat, quality can drift — becoming either increasingly generic or increasingly incoherent over long outputs.',
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
    technicalDeepDive:
      'Tau (τ) is the target perplexity for the Mirostat feedback loop. Perplexity measures how "surprised" the model is by the tokens being generated — it\'s 2^H where H is the cross-entropy.\n\nτ=5.0 (default) targets moderate surprise — coherent but not overly predictable. τ=2.0 targets low surprise — very focused, factual output. τ=8.0 targets high surprise — creative, diverse, sometimes chaotic.\n\nThe feedback loop works as follows: after each token is sampled, the algorithm compares the token\'s actual surprisal to τ. If the sampled token was more surprising than τ, the algorithm tightens sampling (fewer candidates next step). If less surprising, it loosens sampling (more candidates). Over time, output perplexity converges toward τ.\n\nTau only matters when mirostat is set to 1 or 2. The interaction between tau and temperature is multiplicative — high temperature + high tau produces very diverse text; low temperature + low tau produces very deterministic text.',
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
    technicalDeepDive:
      'Eta (η) is the learning rate of the Mirostat feedback controller. After each token is sampled, the internal threshold μ is updated: μ_new = μ_old - η × (surprisal - τ).\n\nHigh η (0.3–1.0): Fast adaptation — μ reacts aggressively to each token. Can oscillate between too tight and too loose sampling, producing inconsistent output quality.\n\nLow η (0.01–0.05): Slow adaptation — μ changes gradually. More stable but takes longer to converge to the target perplexity. May not react fast enough to sudden context shifts.\n\nη=0.1 (default): Balanced — converges within ~20 tokens and remains reasonably stable. This is the recommended value for most use cases.\n\nThe learning rate interacts with the sequence length: for very short outputs (< 50 tokens), higher η helps reach the target faster. For long-form generation, lower η prevents drift. Only meaningful when mirostat is set to 1 or 2.',
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
    technicalDeepDive:
      'Streaming controls how the generated response is delivered from the inference engine to the UI. When enabled, the server sends tokens one at a time (or in small chunks) via Server-Sent Events (SSE), and the UI renders them incrementally.\n\nWith streaming OFF, the entire response is generated server-side before anything is sent to the client. The user sees nothing until the full response is ready — which can mean seconds of blank screen for long answers.\n\nStreaming does NOT affect the model\'s output quality, token probabilities, or sampling behavior. The same tokens are generated in the same order regardless. It only changes the delivery mechanism.\n\nFor MOBIUS specifically: streaming mode enables the glyph shimmer animation (which triggers as symbolic characters appear in the stream) and the CoherenceBar updates (which analyze text as it arrives). Disabling streaming means these real-time features only activate after the full response loads.',
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
    technicalDeepDive:
      'Max tokens sets a hard cap on the number of tokens the model generates. Generation stops when EITHER this limit is reached OR the model emits an end-of-sequence (EOS) token, whichever comes first.\n\nTokenization varies by model, but roughly: 1 token ≈ 4 characters in English, ≈ 0.75 words. So 1000 tokens ≈ 750 words ≈ 1.5 pages of text.\n\nThe value -1 means "no limit" — the model generates until it emits EOS or hits the context window boundary. This is fine for conversational use but risky for automated pipelines where runaway generation could fill the context.\n\nImportant: max_tokens counts only generated tokens, not the prompt. The total context window is prompt_tokens + generated_tokens. If the prompt uses 3000 tokens of a 4096-token context, only 1096 tokens are available for generation regardless of this setting.\n\nFor OpenAI-compatible APIs, this parameter is called "max_tokens." For llama.cpp, it\'s "n_predict." MOBIUS maps between them automatically.',
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
    technicalDeepDive:
      'Stop sequences are strings that, when generated by the model, immediately halt further generation. The stop string itself is excluded from the returned output.\n\nThe model checks for stop sequences after each token is decoded back to text. If the decoded text ends with any stop sequence, generation terminates. This is a post-tokenization string match, not a token-level check.\n\nCommon uses:\n- ["\\n\\n"] — stop after a double newline (end of paragraph)\n- ["User:", "Human:"] — stop before the model starts role-playing the user\n- ["```"] — stop at the end of a code block\n- ["</answer>"] — stop after a structured response tag\n\nMultiple stop sequences can be provided as a JSON array. The model stops at whichever one it hits first. The maximum number of stop sequences varies by backend (typically 4–8 for OpenAI, unlimited for llama.cpp).\n\nStop sequences are particularly important for chat-style prompts where the model might continue generating user turns if not stopped.',
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
    technicalDeepDive:
      'The seed initializes the pseudorandom number generator (PRNG) used during token sampling. When temperature > 0, the model samples from the filtered probability distribution — this sampling step requires randomness. The seed controls that randomness.\n\nSame seed + same prompt + same parameters + same model = deterministic output. This is invaluable for debugging, testing, and reproducing specific generations. Seed -1 (or 0 in some backends) means "use a random seed each time."\n\nCaveats: Reproducibility requires identical conditions. Different batch sizes, different GPU hardware, different model quantizations, or even different llama.cpp versions can produce different outputs from the same seed. Floating-point arithmetic is not perfectly reproducible across hardware.\n\nFor OpenAI API: seed support was added in late 2023 but results are "mostly deterministic" — they document that identical requests may occasionally produce different outputs due to backend infrastructure differences.',
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
    technicalDeepDive:
      'Frequency penalty subtracts a value from each token\'s logit proportional to how many times that token has already appeared in the generated text: logit_i -= frequency_penalty × count(token_i). This is applied before softmax.\n\nThe penalty is cumulative: a token used 3 times gets 3× the penalty. This means frequently-used words become progressively less likely. Negative values do the opposite — they BOOST repeated tokens (useful for poetic forms with intentional repetition).\n\nAt 0: no effect. At 0.5: mild vocabulary diversification. At 1.0: strong push toward novel words. At 2.0: extremely aggressive — the model will contort itself to avoid any repetition. Values above 1.5 often degrade output quality.\n\nFrequency penalty operates at the token level, not the word level. The token "running" and the token " running" (with leading space) are different tokens and tracked separately.\n\nThis penalty applies to the entire generation so far — not a sliding window. Compare with repeat_penalty (local models only) which uses a configurable window via repeat_last_n.',
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
    technicalDeepDive:
      'Presence penalty subtracts a flat value from a token\'s logit if that token has appeared at ALL in the generated text: logit_i -= presence_penalty × (1 if count(token_i) > 0, else 0). Unlike frequency penalty, it doesn\'t scale with count — a token used once is penalized the same as one used ten times.\n\nThe effect is topic-level steering rather than word-level de-duplication. Once the model has mentioned a concept (using its associated tokens), the penalty discourages returning to that concept. This pushes the model to explore new topics rather than elaborating on existing ones.\n\nFrequency and presence penalties are complementary:\n- Frequency penalty alone: "use each word less often" (vocabulary diversity)\n- Presence penalty alone: "talk about new things" (topic diversity)\n- Both together: "use new words about new things"\n\nNegative values encourage returning to previously-mentioned topics — useful for focused, deep-dive discussions on a single subject.\n\nTypical values: 0.0–0.6 for general use. Above 1.0, the model may struggle to maintain coherent threads.',
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
    technicalDeepDive:
      'Repeat penalty is llama.cpp\'s native repetition control. It uses a multiplicative formula rather than the additive formula of OpenAI\'s frequency/presence penalties.\n\nFor a token that has appeared in the last repeat_last_n tokens: if the token\'s logit is positive, it\'s divided by repeat_penalty. If negative, it\'s multiplied by repeat_penalty. This ensures the penalty always reduces the token\'s relative probability.\n\nRepeat penalty = 1.0: no effect (dividing by 1 changes nothing). 1.1 (default): mild discouragement of repetition. 1.3: noticeable effect — rare word repetition. 1.5+: very aggressive — can cause grammatical issues as common function words ("the", "is", "and") get penalized.\n\nThe key difference from frequency_penalty: repeat_penalty only looks within a sliding window of repeat_last_n tokens (default 64), while frequency_penalty considers the entire generation. This makes repeat_penalty more suitable for long-form text where some word repetition over thousands of tokens is natural.\n\nRepeat penalty and frequency/presence penalties can be used simultaneously on local models — they stack.',
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
    technicalDeepDive:
      'Repeat Last N defines the sliding window for the repeat_penalty check. Only tokens within the last N generated tokens are tracked for repetition.\n\nN=64 (default): checks roughly the last 50 words. A token used 100 tokens ago is no longer penalized. This prevents the penalty from being too aggressive in long-form text where naturally revisiting words is expected.\n\nN=0: disables repeat penalty entirely (no window = no tracking). N=-1: considers the ENTIRE generated context — every token ever generated in this response. This is the most aggressive setting and equivalent to how frequency_penalty works.\n\nThe window size creates a tradeoff: small windows allow local repetition (looping within a paragraph), large windows can over-penalize common words that naturally recur in long text.\n\nPractical guidance: 64 works well for conversational responses. 256–512 for longer-form writing. -1 for tasks where ANY repetition is problematic (e.g., brainstorming unique ideas). 0 to rely entirely on frequency/presence penalties instead.',
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
    technicalDeepDive:
      'DRY (Don\'t Repeat Yourself) is a pattern-aware repetition penalty that detects repeated n-gram sequences rather than individual tokens. While repeat_penalty catches single-token repetition, DRY catches structural repetition: repeated phrases, sentence templates, and paragraph patterns.\n\nThe penalty formula: penalty = multiplier × base^(match_length - allowed_length). This exponential scaling means longer repeated sequences are penalized dramatically more than shorter ones.\n\nExample with default settings (multiplier=0.8, base=1.75, allowed=2): a 3-token repeated pattern gets penalty 0.8 × 1.75^1 = 1.4. A 5-token repeated pattern gets penalty 0.8 × 1.75^3 = 4.3. A 10-token repeated paragraph gets penalty 0.8 × 1.75^8 = 82.5 — effectively banned.\n\nDRY is particularly effective at preventing "looping" — when the model gets stuck repeating the same paragraph structure with minor variations. This is a common failure mode of local models at high temperatures.\n\nSet multiplier=0 to disable DRY entirely. Values of 0.5–1.0 provide good anti-repetition without constraining normal text. Values above 2.0 are very aggressive.',
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
    technicalDeepDive:
      'DRY Base is the exponential base in the DRY penalty formula: penalty = multiplier × base^(match_length - allowed_length). It controls how steeply the penalty scales with the length of repeated sequences.\n\nBase=1.0: linear penalty growth (no exponential scaling). Longer patterns are barely penalized more than shorter ones.\n\nBase=1.75 (default): moderate exponential growth. A 5-token match is penalized ~5.4× more than a 2-token match. Good balance between catching problematic loops and allowing natural text.\n\nBase=3.0: aggressive exponential growth. A 5-token match is penalized 81× more than a 2-token match. Very effective at preventing loops but may prevent intentional callbacks or refrains.\n\nThe base interacts strongly with the multiplier: a high base with a low multiplier can have a similar total penalty to a low base with a high multiplier, but the LENGTH SENSITIVITY differs. High base = disproportionately targets long repeated sequences. High multiplier = uniformly penalizes all repetition.',
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
    technicalDeepDive:
      'DRY Allowed Length is the threshold below which repeated n-gram sequences are NOT penalized. In the DRY formula, the exponent is (match_length - allowed_length), so matches at or below the allowed length produce zero or negative exponents.\n\nAllowed=1: every repeated token is penalized (very aggressive). Common words like "the" and "is" will be penalized on second use.\n\nAllowed=2 (default): single repeated words are fine, but repeated bigrams ("in the", "I think") and longer trigger the penalty. Good for natural text where single-word repetition is expected.\n\nAllowed=4: repeated phrases up to 4 tokens long are allowed. Only longer structural repetitions trigger DRY. Use this for technical writing where certain phrases ("the system", "in this case") naturally recur.\n\nAllowed=8: only very long repeated passages trigger DRY. Essentially catches copy-paste loops and nothing else.\n\nThe sweet spot depends on content type: creative writing benefits from allowed=2, technical documentation from allowed=3-4, and code generation from allowed=4+ (since code naturally repeats structural patterns).',
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
    technicalDeepDive:
      'Logit bias directly modifies the raw logit scores before softmax, giving you surgical control over specific tokens. The value is a JSON object where keys are token IDs (integers) and values are bias amounts added to those tokens\' logits.\n\nFormat: {"token_id": bias_value, ...}. Example: {"15043": -100, "2159": 5}\n\nBias values:\n- -100: effectively bans the token (probability → 0 after softmax)\n- -5 to -1: reduces probability moderately\n- 0: no effect\n- +1 to +5: increases probability moderately\n- +100: forces the token to be selected regardless of context\n\nTo find token IDs, you need the model\'s tokenizer. Different models use different tokenizers, so the same word may have different IDs across models. Use a tokenizer tool or the model\'s tokenizer.encode() function.\n\nUse cases: ban profanity (specific token IDs → -100), encourage formal language (boost academic vocabulary tokens), steer away from specific words without changing the prompt, or force output in a particular language.\n\nCaution: This operates at the token level, not word level. The word "hello" might be one token or multiple subword tokens depending on the tokenizer. You need to bias ALL relevant subword tokens for consistent effect.',
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
