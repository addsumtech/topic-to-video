# GSAP 3.15.1 — vendored, unmodified

These four files are GSAP's own minified UMD builds, copied byte for byte from the npm package `gsap@3.15.1`
(published 2026-11-04; tarball shasum `593af220d8bec874b30c4f4b2f459057bf6fe5a1`, the registry's own), `dist/`:

| file | sha256 |
|---|---|
| gsap.min.js | 3d1bea374ab1b703cc5c4105358eec63c4465efdc573931dc116e34a0a190c1b |
| SplitText.min.js | 7b299a6b26b36fd5ce1c0712f31d6d25f98f9a9860778c2d3a78ce8f880f2edf |
| DrawSVGPlugin.min.js | e950c5fb54281dcc8b17212b6e5d2b1dc225c1f7e214192a804ca83a8a8ef2e6 |
| MorphSVGPlugin.min.js | 94274c58a52c17643cedcd08144e3d8dc5b05dde975c39abf7069f9ee5884fe3 |

Each file keeps its copyright banner (the licence forbids removing it): "Copyright 2026, GreenSock. All rights
reserved. Subject to the terms at https://gsap.com/standard-license." GSAP is not covered by this project's MIT
licence. `tests/test_gsapseek.py` pins the hashes above, so an upgrade is a deliberate change (re-copy, re-hash,
re-run the tests).

What follows is the licence's text as published at https://gsap.com/standard-license (retrieved 2026-11-26; effective
date April 30, 2025, last modified May 30, 2025), copied for reference. The page itself is authoritative.

---

## Standard "No Charge" GSAP License

### I. DEFINITIONS

- "GSAP License" means the terms and conditions of this GSAP Software License Agreement.
- "GSAP Products" means any Software made available at gsap.com or any successor sites, including but not limited to
  the GSAP animation library and related plugins, tools, or extensions.
- "Permitted Uses" means the implementation and/or use of GSAP Products on any website, web application, or digital
  interface by any person or entity (which may include, for clarity, those of companies that compete with Webflow in
  other areas of business).
- "Prohibited Uses" means any implementation and/or use of GSAP Products in tools that allow users to build visual
  animations without code that encourages, induces, or materially assists in creating a solution that competes with
  Webflow's visual animation building capabilities.
- "Competitive Products" means any software, tool, or service that enables users to create, edit, or manage
  animations through a visual interface or builder similar to Webflow.

### II. GRANT OF LICENSE

Subject to the terms and conditions of this GSAP License, Webflow grants you a non-exclusive, worldwide license to
use, reproduce, display, and implement GSAP Products solely for Permitted Uses.

### III. RESTRICTIONS

You may not:

- Use any GSAP Products for any Prohibited Uses without prior written consent;
- Reverse engineer any GSAP Products for the purpose of creating Competitive Products;
- Remove or alter any proprietary notices or branding from GSAP Products.

### IV. OWNERSHIP AND INTELLECTUAL PROPERTY

All intellectual property rights in GSAP Products, including but not limited to copyright, patents, trademarks, and
trade secrets, remain the exclusive property of Webflow. This GSAP License does not transfer any ownership rights in
GSAP Products to you.

### V. TERMINATION

Webflow may terminate this GSAP License and revoke your access in its discretion if you fail to comply with any of
these terms and conditions. Upon termination, you must cease all use of GSAP Products and destroy all copies in your
possession.

### VI. MISCELLANEOUS PROVISIONS

- General: This GSAP License is incorporated into and subject to Webflow's Terms of Service available here ("Terms of
  Service"). In the event of any conflict or inconsistency between this GSAP License and the Terms of Service, the
  terms of this GSAP License shall govern in relation to your use of any GSAP Products.
- Amendments: Webflow reserves the right to update or modify this GSAP License at any time by posting the revised
  terms on this website, provided that any such updates or modifications shall not result in any material degradation
  to the security, integrity, or functionality of any GSAP Products. You understand and agree that your continued use
  of any GSAP Products after such revisions to this GSAP License constitutes your acceptance of this GSAP License as
  revised. If you do not accept the revised GSAP License, you are prohibited from using versions of the GSAP Products
  released after the effective date of the revised GSAP License (as well as any updates made to previous versions).
  Notwithstanding, you may continue using previous versions of GSAP Products under the applicable terms licensed to
  you prior to the effective date of the revised GSAP License (for clarity, excluding any updates made thereto).
- No Waiver: Failure of Webflow to enforce any provision of this GSAP License shall not constitute a waiver of future
  enforcement of that or any other provision.

### FAQ (two of the page's questions)

- Is it acceptable for AI tools like ChatGPT, Cursor, Lovable, Webstudio, etc. to generate GSAP code? Absolutely!
  AI-generated code is not a "Prohibited Use".
- Can I really use GSAP in commercial projects without paying anything? Yes, really! Commercial usage is covered under
  the standard license. All of GSAP including the plugins that were formerly "members-only" like SplitText and
  MorphSVG can be used in commercial projects at no charge.

Copyright (c) 2025, Webflow
