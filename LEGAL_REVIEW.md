# Legal review checklist (for the maintainer, not for users)

**This is not legal advice, and neither are the other legal documents in this project.** They are carefully written starting points. Before you publish, show them to a lawyer in your country,
ideally one who knows software, open-source licensing and AI. This list is what to ask them. Replace every placeholder first (see PUBLISHING.md).

## Questions for your lawyer

1. **Company and liability.** Should you publish through a limited-liability company rather than personally? Does it need insurance (technology errors-and-omissions, cyber)? Is the company the owner of all the code (check any contractors and past employers)?
2. **Terms of Use.** Are the disclaimer of warranties, the limit of liability (US$100), the indemnity (Section 9) and the governing-law clause valid and enforceable where you are, and where most of your users are?
   Consumer law in the EU, UK, Canada, Australia and some US states restricts some of these. Choose the governing law and courts you want and fill in the placeholder.
3. **Open source and the Terms together.** The code is Apache-2.0 and the Terms add use rules (Section 2) for the official builds and website only. Does that arrangement hold up, and does it fit how you want to describe the project ("open source")?
4. **GPL components.** Fast mode relies on espeak-ng and phonemizer, which we understand are GPL-licensed. Our installers download them onto the user's computer rather than containing them. Confirm that is acceptable,
   and what changes if you ever ship a Docker image, an offline bundle or a pre-built environment.
5. **Model licenses.** Confirm the commercial-use terms of the Kokoro weights, Chatterbox, the Perth watermarker and the Whisper models, today and again before each release. Ask about any risk that comes from how the models were trained.
6. **EU AI Act, Article 50.** From 2 August 2026, providers of AI systems that generate synthetic audio must mark outputs in a machine-readable, detectable format, and people who publish deepfakes must disclose them.
   A product first released now does not get the extra time to 2 December 2026 that applies to systems already on the market. As we understand it, the Act's open-source exemption does not cover Article 50, and the rules can reach providers
   outside the EU whose output is used in the EU. Voice Studio adds file metadata and an inaudible watermark (see RESPONSIBLE_USE.md). Is that enough ("where technically feasible")? Are you a "provider"? Do you need a visible notice or a C2PA-style provenance record?
7. **Voice, likeness and deepfake laws elsewhere.** Several US states, and other countries, have laws on voice likeness, synthetic media and election content, and regulators have acted against voice impersonation. Do you need extra warnings, or to limit distribution in any country?
8. **Privacy.** The app holds no data on your servers, which removes most obligations. Confirm that the Privacy Notice is accurate for you, and what applies if you ever add analytics, a hosted service, crash reports or accounts.
   Voice recordings can be biometric or sensitive data in some places (for example Illinois and the EU). That matters most if you ever process voices on a server.
9. **Trademark.** Is "Voice Studio" and the logo free to use, and is it worth registering? (The name is generic and probably used by others.)
10. **Contributions.** Are you comfortable with "contributions are Apache-2.0" in CONTRIBUTING.md, or do you want a contributor license agreement or a Developer Certificate of Origin sign-off?
11. **Complaints and takedowns.** You host no user content, but your repository and website can still receive notices. Do you want a formal process or a designated agent?
12. **If you add mobile apps later,** the app stores have their own rules for AI voice and cloning apps.

## What these documents cannot do

- They cannot stop someone suing you, and they cannot bind people who never accepted them.
- They do not replace the safeguards in the product. The strongest protections are structural, and Voice Studio already has them: nothing is hosted or stored on your servers, no data is collected,
  there is no public cloning service, consent is confirmed and recorded, and output is marked.
- Keep these safeguards when you change things. A hosted version that clones voices for the public would change your risk a great deal and should be reviewed first.
