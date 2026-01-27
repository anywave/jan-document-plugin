LLM Engine Staging Directory
============================

Place the following files here BEFORE compiling the Inno Setup installer:

Required:
  - llama-server.exe    (from llama.cpp release, Vulkan build)

Vulkan DLLs (required for GPU acceleration):
  - vulkan-1.dll        (or whichever Vulkan runtime DLLs llama-server needs)

Where to get llama-server (Vulkan build):
  https://github.com/ggerganov/llama.cpp/releases
  Download: llama-*-bin-win-vulkan-x64.zip

If this directory is empty when the installer is compiled, the bundled
LLM server will be omitted and users will need Jan AI or another
OpenAI-compatible server running on port 1337.
