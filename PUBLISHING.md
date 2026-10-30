# Publishing guide (for the maintainer)

Step by step, from this folder to a public project people can download. Nothing here needs you to be a programmer,
but you do need to type a few commands. Where something could not be tested in advance, it says so.

## 0. Decide how your name appears

- **Credit your company, name the product separately.** The product is "Voice Studio" (you can rename it, see below). Your company appears as the publisher:
  in the copyright line, the app footer, the website and the installers. The Apache-2.0 license requires anyone who copies the project to keep that credit.
- **Make sure the company owns the code.** If people other than you wrote any of it, check you have their permission to publish it under this license.
- **Check the product name** is not already used: search GitHub, Google and your country's trademark database. If you rename it, search the whole project for "Voice Studio" and replace it.
- **Do not put other companies' names or logos in the product name or the app.** Mentioning a competitor in plain, truthful comparisons (like the website FAQ) is fine; keep it factual and avoid claiming equal quality.

## 1. Create the repository

1. Create a free account at github.com (or use your company's organization).
2. Create a new **public** repository named `voice-studio`. Leave it empty (no README, no license).

## 2. Fill in your details, once

On your computer, in this folder:

```bash
python tools/set_identity.py --company "Your Company" --repo your-github-name/voice-studio \
    --email you@yourcompany.com --jurisdiction "England and Wales"
python tools/set_identity.py --check          # should say "Nothing left to fill in."
```

`--jurisdiction` is whose law governs the Terms of Use (for example "the State of Delaware, USA" or "England and Wales"). Ask your lawyer which to choose.

Optional extras: `--site https://your-own-website.example` (otherwise your GitHub Pages address is used) and `--company-url https://yourcompany.example`
(links your name in the app footer). Run it only once. If you make a mistake, restore the files from Git and run it again.

## 3. Legal review (do this before going public)

The project includes these documents: `TERMS_OF_USE.md`, `PRIVACY.md`, `RESPONSIBLE_USE.md`, `TRADEMARKS.md`, `CODE_OF_CONDUCT.md`, `THIRD_PARTY_LICENSES.md`, `NOTICE` and the Apache `LICENSE`.
They are careful starting points, **not legal advice, and they cannot guarantee you will never face a legal problem.** Give them to a lawyer in your country
together with `LEGAL_REVIEW.md`, which lists exactly what to ask. Two things deserve particular attention:

- **The EU AI Act (Article 50)** applies from 2 August 2026 and requires providers of tools that generate synthetic audio to mark the output in a machine-readable way.
  Voice Studio marks every file in its metadata and adds an inaudible watermark, but whether that is enough for you is a question for your lawyer.
- **The GPL note** at the bottom of `THIRD_PARTY_LICENSES.md`: do not publish a Docker image or an offline bundle that contains the pronunciation packages without legal advice.

After you or your lawyer edit any of the `.md` documents, rebuild the web pages the app and website show: `pip install markdown` then `python tools/build_legal.py`.
If you change the Terms in a way that matters, raise the version number in `app/legal.py` **and** at the top of `TERMS_OF_USE.md`, so every user is asked to accept them again.

Keep the safeguards that protect you: do not host users' scripts or voices on a server, do not add tracking, do not offer public voice cloning online, and keep the consent step and the AI-generated marking.

## 3b. Other review before going public

- Read `NOTICE`, `RESPONSIBLE_USE.md` and the website FAQ in `docs/index.html`, and change anything that does not sound like you.
- **Licenses:** confirm the table in `THIRD_PARTY_LICENSES.md`. After a normal install, run `pip install pip-licenses` and then `pip-licenses --format=markdown` inside the app's environment.
  Pay attention to the GPL note at the bottom of that file. Have a lawyer glance at it if you can.
- Replace the screenshots if you want new ones: `python tools/make_screenshots.py` (needs `pip install playwright` and `playwright install chromium`).

## 4. Upload it

```bash
git init
git add .
git commit -m "First public release"
git branch -M main
git remote add origin https://github.com/your-github-name/voice-studio.git
git push -u origin main
```

On GitHub the **Actions** tab should now show the tests running. Open the first run: it should pass on all three systems.
If a system fails, read the red step, it usually names the problem.

## 5. Turn on the website

Repository **Settings > Pages > Source: GitHub Actions**. Then run **Actions > Deploy website > Run workflow**.
Your site appears at `https://your-github-name.github.io/voice-studio/`, with the browser edition at `/try/`.

**The browser edition has only been tested with a stand-in for the voice library.** Open `/try/` yourself, make a short voiceover in Chrome, and make sure
it downloads the model and plays audio. It loads the `kokoro-js` library from a public content network (jsDelivr) and the model from Hugging Face.
If something changed on their side, the page shows a clear error message.

## 6. Try the installers before announcing anything

**Actions > Build installers > Run workflow** (leave the version as `0.0.0-test`). After a few minutes, three downloads appear on the run's page:
Windows, Mac and Linux. **Install each on a real computer.** This is the most important step:

- The installer workflows have not been run on GitHub yet. The Linux installer's setup logic was tested end to end; the Windows and Mac installers were
  written carefully but could not be tried, so expect one or two small fixes.
- If something fails, copy the red error from the Actions page (or `setup.log` in the app's data folder, see the README) and fix it before releasing.
- On Windows, if you see "Windows protected your PC": that is the unsigned-installer warning, see step 9.

### What a new user experiences (so you know what to expect)

1. They download one file from your Releases page or website and **double-click it**. Nothing can run by itself before that; this is how all downloaded software works.
2. **Windows:** the installer adds the icons, then a window sets everything up. **Mac:** they open the app and a Terminal window sets it up. **Linux:** the same, from the file.
3. The one-time setup **needs internet**. It downloads Python, the libraries, and the Fast mode and caption models. It takes several minutes.
4. Voice Studio then opens in its own window and shows the Terms of Use. After they accept, it works **with no internet** for Fast mode and captions.
5. Voice cloning models are several GB, so they are optional: **This computer > Use offline**, or they download the first time Clone mode is used.

A fully offline installer (everything bundled) is possible but would be several GB per system, and bundling the GPL-licensed pronunciation packages needs legal advice first.

## 7. Publish version 1.0.0

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds the three installers and creates a public Release with them. The download buttons on your website point to the **latest release**
using fixed file names, so they keep working for every new version. Check each button after the release appears.

For later versions: change the number in `VERSION`, commit, then tag and push again (`v1.0.1`, `v1.1.0`, and so on).

## 8. Make it easier to find and install

- **winget (Windows):** after the release exists, follow `packaging/winget/README.md`.
- **Homebrew (Mac):** create a repository called `homebrew-tap`, put `packaging/homebrew/voice-studio.rb` in a `Casks` folder, and fill in the version and checksum.
- **Pinokio:** it works as soon as the repository is public: in Pinokio, paste the repository address into Discover. The Pinokio files were written from its documentation and have not been run. To be listed on Pinokio's own Discover page, follow their instructions for submitting scripts.
- **Share it honestly:** a short screen recording of a script becoming audio is the best introduction. Good places include your own channel, communities of video creators and editors, and "Show HN". Say what it is, what it is not (it can be slower or less polished than paid services), and that it is free.

## 9. Optional: remove the security warnings

- **Windows:** the SignPath Foundation says it offers free code signing to open-source projects. Check their current requirements and apply. Until then, the website tells visitors how to get past the warning.
- **Mac:** removing the warning needs a paid Apple Developer account (about $99 a year at the time of writing). `packaging/macos/build_dmg.sh` already supports signing and notarization through environment variables; you would add a step to the workflow that imports your certificate and passes the secrets.
- **Linux:** no signing is needed.

## 10. Optional: donations

Create a GitHub Sponsors profile or an Open Collective page, then edit `.github/FUNDING.yml` (uncomment one line and put in your name). GitHub then shows a Sponsor button.
Add the link to the website footer too.

## 11. Keeping it healthy

- Reply to issues, even with "thanks, looking into it". It is what makes people stay.
- Keep the **Tests** workflow green. It needs no models, so it is quick.
- When Chatterbox, Kokoro or Whisper change their requirements, the installers install the latest versions on first launch, so test an install every few months.
- Keep an eye on **Responsible use**: if you learn of misuse of the project itself, you can state your position in the repository.
