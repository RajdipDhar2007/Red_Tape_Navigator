# Accessibility

Government paperwork is for everyone, so Red Tape Navigator must be usable by everyone: people with visual, hearing, motor or cognitive disabilities, people on small phones and slow connections, and people who read Hindi or Bengali rather than English.

## Our commitment

We aim for the **Web Content Accessibility Guidelines (WCAG) 2.1, level AA** across the web app. This is a goal we are working towards, not a certification. We treat accessibility problems as bugs, not as optional polish.

## What is already in place

- **Three languages:** the whole interface and the backend text are available in English, Hindi and Bengali. The page language (`lang`) is set correctly, and each language name in the picker is marked with its own language.
- **Keyboard use:** pages can be used with the keyboard, with a visible focus outline and a **"Skip to main content"** link.
- **Screen readers:** form fields have labels, error messages are announced (`role="alert"`), and progress and upload status use live regions. Each page has a title and one main heading, and decorative icons are hidden from assistive technology.
- **Reduced motion:** all animation and confetti are switched off when your system asks for reduced motion.
- **Plain language:** one or two questions at a time, validation messages in your own language, and answers are saved as you go.
- **Voice input** for the goal sentence, where your browser supports speech recognition.
- **Responsive layout:** works on phone screens and zooms with the browser.
- **Audit so far:** a DOM accessibility audit of the home, account, privacy, terms, reset and officer pages checked the page language, titles, a single main heading, form labels, accessible names and landmarks.

## Supported environments

Our automated browser tests run on desktop Chrome and on an emulated Android phone (Pixel 7). We expect it to work in current Firefox, Edge and Safari, but we have not tested them systematically. Assistive technology we aim to support: NVDA and JAWS on Windows, VoiceOver on macOS and iOS, and TalkBack on Android.

## Known limitations

We prefer to be open about these:

- **Not yet tested with real assistive technology on real devices.** The screen-reader and real-phone tests are still on our launch checklist.
- **Hindi and Bengali wording** has not been reviewed by native speakers yet, which can affect clarity for screen-reader users.
- **Voice input** depends on the browser's speech recognition, which is not available in every browser or language.
- **Colour contrast** has been designed to meet AA, but has not been audited tool-by-tool on every screen.
- **Official forms and PDFs** come from the issuing authorities (or are placeholders). Their accessibility is outside our control, and a filled PDF may not be tagged for screen readers. We provide the same information as on-screen fields and a text key-in sheet.
- **Charts and screenshots** in the README and documentation do not all have long text descriptions.

## Tell us about a barrier

If something does not work for you, we want to hear about it:

1. Open an issue with the **Accessibility barrier** form: <https://github.com/RajdipDhar2007/Red_Tape_Navigator/issues/new/choose>
2. Tell us the page, what you tried to do, what happened, and the browser and assistive technology you use. Screenshots help, but please hide any personal data.
3. If you prefer not to use a public issue, contact the repository owner through GitHub (**RajdipDhar2007**).

We will acknowledge your report as soon as we can, tell you what we plan to do, and fix barriers that stop people from completing a task first.

## Standards and references

- [WCAG 2.1](https://www.w3.org/TR/WCAG21/)
- [Rights of Persons with Disabilities Act, 2016](https://disabilityaffairs.gov.in/) (India), and the Indian government's guidelines for accessible websites (GIGW)

This statement is reviewed whenever the interface changes in a way that affects accessibility.
