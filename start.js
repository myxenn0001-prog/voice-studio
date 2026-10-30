// Pinokio start script: runs the app and tells Pinokio which address to open.
module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        venv: "venv",
        env: {
          VOICESTUDIO_OPEN_BROWSER: "0",
          VOICESTUDIO_DATA: "{{path.resolve(cwd, 'data')}}",
        },
        message: ["python run_server.py"],
        on: [{ event: "/(http:\\/\\/127\\.0\\.0\\.1:\\d+)/", done: true }],
      },
    },
    {
      method: "local.set",
      params: { url: "{{input.event[1]}}" },
    },
  ],
}
