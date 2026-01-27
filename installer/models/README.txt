Model Staging Directory
=======================

Place GGUF model files here BEFORE compiling the Inno Setup installer:

Recommended model:
  Qwen 2.5 7B Instruct (q4_k_m quantization)
  Files:
    - qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
    - qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf

Where to download:
  https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF

Total size: ~5 GB

If this directory is empty when the installer is compiled, no model
will be bundled and users will need to provide their own model or
use Jan AI's built-in model management.
