// Pinokio launcher for Voice Studio. Pinokio is a one-click launcher for open-source apps:
// install Pinokio, paste this repository's URL into Discover, then press Install and Start.
module.exports = {
  version: "2.0",
  title: "Voice Studio",
  description: "Free, offline voiceovers and captions on your own computer. Built-in voices in several languages, optional voice cloning.",
  icon: "icon.png",
  menu: async (kernel, info) => {
    const installed = info.exists("venv")
    const running = {
      install: info.running("install.js"),
      start: info.running("start.js"),
    }
    if (running.install) {
      return [{ default: true, icon: "fa-solid fa-plug", text: "Installing", href: "install.js" }]
    }
    if (installed) {
      if (running.start) {
        const local = info.local("start.js")
        if (local && local.url) {
          return [
            { default: true, icon: "fa-solid fa-rocket", text: "Open Voice Studio", href: local.url },
            { icon: "fa-solid fa-terminal", text: "Terminal", href: "start.js" },
          ]
        }
        return [{ default: true, icon: "fa-solid fa-terminal", text: "Terminal", href: "start.js" }]
      }
      return [
        { default: true, icon: "fa-solid fa-power-off", text: "Start", href: "start.js" },
        { icon: "fa-solid fa-plug", text: "Update", href: "install.js" },
      ]
    }
    return [{ default: true, icon: "fa-solid fa-plug", text: "Install", href: "install.js" }]
  },
}
