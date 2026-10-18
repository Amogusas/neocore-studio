# NEOCORE STUDIO

High-performance digital production website featuring real-time 3D WebGL visuals, procedural Web Audio synthesizer, interactive project cost calculator, universal checkout hub (SBP, Cards, B2B Invoices), 4-step project brief builder, and instant Telegram Bot integration.

## Key Features

- **Interactive 3D WebGL Engine**: Three.js viewport with real-time physics, selectable geometries (crystal, torus knot, sphere), wireframe toggle, and click-acceleration RPM combo counter.
- **Procedural Web Audio System**: Synthesized interface feedback, chord arpeggios, 808 sub-bass, interactive piano keyboard, and procedural Lo-Fi chillwave generator.
- **Lead Capture & Telegram Dispatch**: Real-time structured notifications for contact requests, tariff purchases, and technical project briefs sent directly via Telegram Bot API.
- **Universal Checkout Hub**: SBP (Faster Payments System) QR generator with 15-minute countdown timer, credit/debit card validation form with input formatting, and B2B invoice generation with INN verification.
- **Interactive Project Brief (Wizard)**: 4-step requirements onboarding with automatic localStorage draft persistence, ticket assignment (#BR-2026-XXXX), and summary export.
- **Dynamic Cost Calculator**: Multi-parameter estimate generator with instant quote copy and direct 30% advance deposit integration.
- **Enterprise Compliance**: 152-FZ / GDPR Privacy Policy modal, Cookie consent management, and Schema.org ProfessionalService structured metadata.

## Tech Stack

- HTML5 / CSS3 (Custom design system, CSS variables, dark/light themes, view transitions)
- Vanilla JavaScript (Zero framework overhead, ES6+)
- Three.js (WebGL 3D canvas)
- Web Audio API (Procedural sound synthesis)
- Telegram Bot API (Direct serverless notifications)

## Deployment

The project is completely self-contained within `index.html` and requires no build step.

### GitHub Pages Setup

1. Push this repository to GitHub.
2. In the repository settings, navigate to **Pages** (under Code and automation).
3. Under **Build and deployment** > **Source**, select **Deploy from a branch**.
4. Choose branch `main` and folder `/ (root)`.
5. Click **Save**. The website will be live at `https://<username>.github.io/<repo-name>/`.
