# Responsible use

**Version 1.1**

Voice Studio makes realistic synthetic speech, and its Clone mode can imitate a voice from a short recording. That is useful for creators, and it can be misused.
Please use it the way you would want others to use it on you.

## What we ask

- **Get permission.** Only clone a voice that is yours, or that belongs to someone who has clearly agreed. The app asks you to confirm this each time you add a voice, and records that you did. Please mean it.
- **Do not deceive.** Do not use it to impersonate a real person, to fake an endorsement, to commit fraud, to get past voice-based identity checks, to harass or threaten anyone, or to spread disinformation
  such as fake political statements.
- **Be open about synthetic audio** where it matters: where people would reasonably expect a real human, where the law requires disclosure, or where a platform's rules ask for it.
  Many countries and platforms now require realistic AI-generated audio to be labelled.
- **Respect the law.** Voice, likeness, publicity and privacy rights differ by country, and several places have specific laws about synthetic voices and deepfakes. You are responsible for how you use the audio.
- **Keep recordings private.** Voice samples are personal data. Voice Studio stores them only on your computer, in the `data/voices` folder. Do not share someone else's sample without their permission.

## What is built in

- Clone mode needs a consent confirmation before a voice can be added. The confirmation is recorded with the voice, with the time and the version of the Terms.
- **Every file Voice Studio makes is marked as AI-generated.** The file carries a note in its metadata ("AI-generated speech. Made with Voice Studio."), and audio is watermarked with an inaudible
  watermark: the Clone-mode model adds its own, and for other voices the app applies the same open-source watermarker when it is installed.
  Metadata is easy to strip and a watermark can be weakened by editing audio, so these marks help but cannot guarantee that synthetic audio is detected. **Please do not remove them.**
- Nothing is uploaded: Voice Studio runs on your computer and has no server that can see your scripts or voices.

## How this relates to the license and the Terms

If you use our official builds or website, the [Terms of Use](TERMS_OF_USE.md) make the rules in its Section 2 part of an agreement, and removing the markings is not allowed.
For anyone using the source code under the Apache-2.0 license, this document is a **request and a community norm**, not an extra condition on that license.
Voice Studio cannot monitor or stop what people do with their own copies. If you find a misuse of the project itself, such as a fork that removes the consent step and promotes impersonation,
you can tell us at myofficialemail89@gmail.com.
