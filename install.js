// Pinokio install script: creates a private Python environment and installs Voice Studio into it.
module.exports = {
  run: [
    {
      // NVIDIA GPU
      when: "{{gpu === 'nvidia'}}",
      method: "shell.run",
      params: {
        venv: "venv",
        message: "uv pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124 --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match",
      },
    },
    {
      // Windows or Linux without an NVIDIA GPU: the small CPU build
      when: "{{gpu !== 'nvidia' && platform !== 'darwin'}}",
      method: "shell.run",
      params: {
        venv: "venv",
        message: "uv pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match",
      },
    },
    {
      // Mac: the standard build already supports the Apple GPU
      when: "{{platform === 'darwin'}}",
      method: "shell.run",
      params: { venv: "venv", message: "uv pip install torch==2.6.0 torchaudio==2.6.0" },
    },
    {
      method: "shell.run",
      params: { venv: "venv", message: "uv pip install -r requirements.txt" },
    },
    {
      // Each engine is installed on its own so one failure does not stop the others
      method: "shell.run",
      params: { venv: "venv", message: "uv pip install chatterbox-tts" },
    },
    {
      method: "shell.run",
      params: { venv: "venv", message: "uv pip install \"kokoro>=0.9.4\"" },
    },
    {
      method: "shell.run",
      params: { venv: "venv", message: "uv pip install faster-whisper" },
    },
    {
      method: "notify",
      params: { html: "Voice Studio is installed. Press Start." },
    },
  ],
}
