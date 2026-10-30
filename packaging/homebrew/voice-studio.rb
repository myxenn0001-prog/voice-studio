# Homebrew cask for Voice Studio (Apple Silicon).
# Easiest route: create a repository named "homebrew-tap" under your GitHub account, put this file in
# its "Casks" folder, and people can then run:
#     brew install --cask myxenn0001-prog/tap/voice-studio
# Update `version` and `sha256` for each release:   shasum -a 256 VoiceStudio-macOS.dmg
cask "voice-studio" do
  version "1.0.0"
  sha256 "REPLACE_WITH_SHA256_OF_THE_RELEASE_FILE"

  url "https://github.com/myxenn0001-prog/voice-studio/releases/download/v#{version}/VoiceStudio-macOS.dmg"
  name "Voice Studio"
  desc "Free offline voiceovers and captions"
  homepage "https://myxenn0001-prog.github.io/voice-studio"

  depends_on arch: :arm64
  depends_on macos: ">= :monterey"

  app "Voice Studio.app"

  zap trash: "~/Library/Application Support/VoiceStudio"
end
