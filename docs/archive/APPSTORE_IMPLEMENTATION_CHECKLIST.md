# App Store Review Checker — 2026 Implementation Checklist

This document tracks specific changes needed to adapt the appstore-review-checker skill with 2026 Apple guidelines.

---

## File: `references/guidelines.md`

### Section 1.3: Kids Category — EXPAND with Regional Laws

**Current:**
```markdown
### 1.3 Kids Category

| ID | Guideline | What to Check |
|----|-----------|---------------|
| 1.3-a | No links outside parental-gated areas | If Kids Category: verify no external links, purchasing prompts, or distractions outside parental gates |
| 1.3-b | No third-party analytics or advertising | If Kids Category: verify no third-party SDKs for analytics or ads (limited exceptions require human review) |
| 1.3-c | No IDFA collection or identifiable info transmission | If Kids Category: verify no device identifier collection or personal data transmission |
| 1.3-d | Comply with COPPA and applicable children's privacy laws | If Kids Category: verify compliance with children's privacy regulations |
```

**Action:** Replace with:
```markdown
### 1.3 Kids Category (COPPA/GDPR/Regional Compliance)

| ID | Guideline | What to Check |
|----|-----------|---------------|
| 1.3-a | No links outside parental-gated areas | If Kids Category: verify no external links, purchasing prompts, or distractions outside parental gates |
| 1.3-b | No third-party analytics or advertising | If Kids Category: verify no third-party SDKs for analytics or ads (limited exceptions require human review); no behavioral tracking |
| 1.3-c | No IDFA collection or identifiable info transmission | If Kids Category: verify no device identifier collection or personal data transmission |
| 1.3-coppa | COPPA (US, under 13): parental consent required | If app targets children under 13: verify parental consent mechanism, no behavioral ads, no marketing, data minimization |
| 1.3-gdpr | GDPR (EU, under 16): parental consent varies by age | If app targets EU minors: verify parental consent per GDPR Article 8, age verification system, clear privacy policy |
| 1.3-lgpd | LGPD (Brazil, under 13): parental consent required | If app targets Brazilian children under 13: verify parental consent, limited data collection |
| 1.3-no-marketing | No marketing or profiling of kids | If Kids Category: verify no behavioral profiling, no interest-based ads, no dark patterns targeting children |
```

**Estimated changes:** ~10 lines added

---

### Section 2.5.16-17: Add App Clips & Matter Support

**Current (around line 140-141):**
```markdown
| 2.5.16 | Widgets, extensions, notifications related to app content | Verify widgets/extensions serve content from the main app; App Clips in main binary with no ads |
| 2.5.17 | Matter support uses Apple's Matter framework | If smart home: verify using Apple's Matter SDK |
```

**Action:** Clarify and expand:
```markdown
| 2.5.16-widgets | Widgets must display app-related content | Verify widgets show real-time data from main app; not standalone mini-apps |
| 2.5.16-extensions | Extensions must include functionality (not just passthrough) | If extensions: verify they have meaningful features, settings, help screens |
| 2.5.16-clips | App Clips bundled in main binary with no advertising | If App Clips: verify bundled with main app; no interstitial ads; clear call-to-action |
| 2.5.17-matter | Smart home/Matter integration uses Apple's Matter framework | If smart home: verify using official Apple Matter SDK, not third-party alternatives |
| 2.5.17-homekit | HomeKit integration follows HomeKit Accessory Protocol | If HomeKit: verify proper accessory setup, authentication, no feature gating |
```

**Estimated changes:** ~5 lines modified/added

---

### Section 2.7: Add new section for "Apple Intelligence" & AI Features (if applicable)

**Note:** 2026 guidelines may include new AI-specific rules. For now, this is a watch area.

**Action:** Monitor for:
- On-device vs cloud processing transparency
- User data consent for AI training
- Accuracy/hallucination disclaimers

---

### Section 3.1.5: ENHANCE Cryptocurrency Section

**Current (around line 168-169):**
```markdown
| 3.1.5 | Cryptocurrency apps: proper licensing and entity requirements | If crypto wallet/exchange/mining: verify organization status, proper licensing, no on-device mining |
```

**Action:** Expand to:
```markdown
| 3.1.5-wallet | Crypto wallets: secure key management from registered entity | If wallet: verify developer is registered entity (not individual reseller); secure key storage; clear ToS; user backup mechanism |
| 3.1.5-exchange | Exchanges require proper jurisdiction licensing | If exchange: verify legal entity status, licensed in relevant jurisdictions (FinCEN, FCA, etc.); compliance with money transmission rules |
| 3.1.5-mining | Mining: off-device only; user consent required | Verify no on-device CPU/GPU mining; if off-device mining: disclose power/data costs, get explicit user consent |
| 3.1.5-token | Tokens/NFTs: collectible only; cannot gate features | Verify tokens are viewable/tradeable; no paywalls or feature gating based on token ownership |
| 3.1.5-disclosure | Crypto risks: clear disclosure required | If crypto features: verify disclaimer about market volatility, custody risks, regulatory uncertainty |
```

**Estimated changes:** ~8 lines (replaces 1 line, adds 7)

---

### Section 4.7: SIGNIFICANTLY EXPAND Mini-Apps/Streaming/Chatbots

**Current (around line 232-240):**
```markdown
### 4.7 Mini Apps, Streaming, Chatbots, Emulators

| ID | Guideline | What to Check |
|----|-----------|---------------|
| 4.7.1 | Hosted software follows privacy guidelines, has filtering/reporting/blocking | If hosting mini-apps/games: verify moderation, privacy compliance, reporting |
| 4.7.2 | No native API exposure without Apple permission | Verify hosted content doesn't access native APIs |
| 4.7.3 | Data/privacy permissions require per-instance user consent | Verify each hosted app requests its own permissions |
| 4.7.4 | Provide index of software with universal links | If hosting content: verify software catalog with deep links |
| 4.7.5 | Age identification and restriction for inappropriate content | If hosting varied content: verify age gating system |
```

**Action:** Completely rewrite with details:
```markdown
### 4.7 Mini Apps, Streaming Games, Chatbots, Emulators

**Overview:** Apps that host, stream, or provide access to third-party software (mini-games, streaming games, interactive content, chatbots, emulators) must enforce strict controls.

| ID | Guideline | What to Check |
|----|-----------|---------------|
| 4.7.1-guidelines | Hosted software must follow all App Store Review Guidelines | If hosting content: verify each hosted app/game follows all 5 guideline sections (safety, performance, business, design, legal) |
| 4.7.1-content | Content moderation & filtering system required | If hosting user-generated content: verify content filtering (text, images, video), reporting/flagging mechanism, blocking/removal process |
| 4.7.2-api | No native API access to hosted software | Verify hosted content cannot access camera, location, contacts, health data, calendar, etc. without per-instance permission |
| 4.7.3-consent | Per-instance permission consent required | Each hosted app must independently request permissions (not inherited from main app); user clearly sees which hosted app requests what data |
| 4.7.4-catalog | Software index/catalog with universal links | If hosting content: verify directory/index of all available software with deep links; no hidden or unapproved content |
| 4.7.5-age-gating | Age restriction system for mixed content | If hosting varied content (games for 4+ and 17+): verify age gating, content filtering by age, clear age ratings |
| 4.7.6-malware | No stolen, pirated, or infringing software | Verify hosted software screened for piracy, malware, copyright infringement |
| 4.7.7-runtime | Custom runtimes allowed; native binary loading prohibited | If supporting Python, Lua, JavaScript: verify sandboxing; **no native binary execution** |
| 4.7.8-streaming | Game streaming: must display gameplay, not just library | If streaming games (Xbox Cloud, PS Now, etc.): verify showing live gameplay, not just menu selection |
| 4.7.9-mini-payment | In-app purchases in hosted content must use IAP OR allowed alternative | Verify any digital purchases use Apple IAP (or allowed exceptions per 3.1.3) |
| 4.7.10-links | No outbound links from hosted content (with limited exceptions) | Verify hosted apps don't link outside ecosystem; exceptions: deep links to other approved hosted content |
| 4.7.11-account-delete | Hosted content account deletion | If hosted apps allow accounts: verify deletion mechanism follows 5.1.1-v-delete rules |
| 4.7.12-privacy-policy | Privacy policy covers all hosted software | Verify privacy policy discloses all data collected across main app + hosted content; explicit for each hosted app's data use |
```

**Estimated changes:** ~20 lines (was 5 lines, now ~25 lines with details)

---

### Section 5.1.1-ii: ENHANCE Consent & Consent Withdrawal

**Current (around line 270-272):**
```markdown
| 5.1.1-ii | User consent for data collection (even anonymous) | Verify consent mechanism before any data collection; clear purpose strings |
| 5.1.1-ii-withdraw | Easy consent withdrawal method | Verify users can revoke data permissions easily |
```

**Action:** Expand:
```markdown
| 5.1.1-ii | User consent for data collection (even anonymous) | Verify **explicit** user consent before any data collection; clear, specific purpose strings; not buried in ToS |
| 5.1.1-ii-clarity | Consent UI: clear, not dark patterns | Verify consent dialog uses plain language, equal prominence for "Agree"/"Decline" buttons; no pre-checked boxes; no impossible-to-refuse patterns |
| 5.1.1-ii-withdraw | Easy in-app consent withdrawal | Verify users can revoke permissions within app in Settings/Privacy section (in addition to iOS system settings); no confirmation delays or re-prompting after denial |
| 5.1.1-ii-no-force | No forced consent; app must work with declined permissions | Verify app doesn't require consent for features that don't need the data; no repeated permission prompts after user declines |
```

**Estimated changes:** ~6 lines

---

### Section 5.1.1-v-delete: EMPHASIZE Account Deletion (Move to Top Rejection Trigger)

**Current (around line 275):**
```markdown
| 5.1.1-v-delete | Account creation must allow deletion within app | If accounts exist: verify in-app account deletion mechanism |
```

**Action:** Expand with emphasis:
```markdown
| 5.1.1-v-delete | Account creation must allow **in-app deletion** (critical, heavily enforced) | If accounts exist: verify self-service account deletion in app; no "contact support" requirement; includes data deletion; tested and working |
| 5.1.1-v-delete-flow | Account deletion flow must be discoverable and frictionless | Verify deletion option visible in Settings/Account section; single-tap deletion (max 2 steps); no delay or confirmation hell |
| 5.1.1-v-delete-data | Data deletion upon account deletion | Verify user data (posts, photos, messages, preferences) deleted or anonymized; option to export before deletion |
```

**Estimated changes:** ~5 lines

---

### Section 5.1.3: EXPAND Health & Fitness Data (Research Protocols)

**Current (around line 288-292):**
```markdown
| 5.1.3-i | Health/fitness data not shared for ads/marketing/data mining | If health app: verify no data monetization; disclose specific data collected |
| 5.1.3-ii | No false/inaccurate health data; no personal health info in iCloud | If health data: verify accuracy standards and storage security |
| 5.1.3-iii | Health research requires informed consent with specific disclosures | If health research: verify comprehensive consent flow |
| 5.1.3-iv | Health research requires ethics board approval | If health research: verify IRB/ethics board documentation |
```

**Action:** Enhance with specifics:
```markdown
| 5.1.3-i | Health/fitness data not shared for ads/marketing/data mining | If health app: verify no data monetization; no sharing with third parties for ad targeting; disclose specific data collected |
| 5.1.3-ii | Health data accuracy and storage security | If health data: verify accuracy claims backed by research; no personal health info in unencrypted iCloud sync; per-app iCloud container recommended |
| 5.1.3-iii-consent | Health research: comprehensive informed consent | If health research: verify consent discloses study duration, data usage, withdrawal mechanism, funding source, IRB approval; plain-language summary; easy withdraw process |
| 5.1.3-iii-irb | Health research: ethics board (IRB) approval mandatory | If health research: verify IRB/ethics board documentation available; protocol reviewed for data minimization |
| 5.1.3-iv-minors | Health research: special rules for minors | If collecting health data from under-18: verify parental consent, assent from minor, extra privacy protections |
| 5.1.3-withdrawal | Health research: easy data withdrawal | Verify users can request data deletion; withdrawal doesn't affect app functionality |
| 5.1.3-no-fingerprinting | Health data: no surreptitious tracking or profiling | Verify no fingerprinting users via health patterns; no cross-device tracking via health data |
```

**Estimated changes:** ~8 lines

---

### New Section: Alternative App Distribution (Notarization in EU/Japan)

**Add new section after 5.2:**

```markdown
---

## 6. NOTARIZATION (EU & Japan Alternative Distribution)

**Overview:** Apps distributed via Notarization in the EU (Digital Markets Act) and Japan must comply with modified App Store Review Guidelines marked with 🔑 (ASR & NR icon).

For developers using Alternative App Distribution channels in these regions, these guidelines apply in addition to standard rules:

| ID | Guideline | What to Check |
|----|-----------|---------------|
| 6.1-dma | EU DMA compliance (Digital Markets Act) | If distributing in EU via Notarization: verify marketplace terms comply with DMA, no anti-competitive behavior, transparent curation |
| 6.2-privacy-eu | EU privacy laws (GDPR, ePrivacy Directive) | If EU distribution: verify GDPR Article 6 lawful basis, cookies/tracking consent, data transfer mechanisms |
| 6.3-japan | Japan compliance (APPI, Act on Protection of Personal Information) | If Japan distribution: verify APPI compliance, data residency requirements, explicit consent mechanisms |
| 6.4-notarization-security | Notarized apps: code signature, runtime checks | Verify app properly notarized, code signed, passes runtime security checks |

**Note:** This is an informational section. The same App Store Review Guidelines (Sections 1-5) apply; these are regional emphasis areas.
```

**Estimated changes:** ~15 lines (new section)

---

## File: `SKILL.md`

### Section: Update "Top 20 Rejection Triggers" Reference

**Current (in Phase 2: Run the Audit):**
```markdown
- Start with the "Top 20 Rejection Triggers" at the bottom of the guidelines reference — these cause the most rejections and should be checked first
```

**Action:** Clarify:
```markdown
- Start with the "Top 20 Rejection Triggers" at the bottom of the guidelines reference — these cause the most rejections and should be checked first. **Priority:** Account deletion, privacy policy, and metadata issues are top 3 in 2026; focus on these first as enforcement has increased significantly.
```

**Estimated changes:** ~1 sentence addition

---

## File: `references/guidelines.md` — Update Top 20 at Bottom

**Current (lines 309-332):**
```markdown
## Quick Reference: Top 20 Rejection Triggers

These are the guidelines most commonly causing rejection — audit these first:

1. **5.1.1-i** — Missing or inaccessible privacy policy
2. **2.1-a** — App crashes, broken features, placeholder text
3. **2.3** — Misleading metadata (description doesn't match app)
4. **4.2** — Insufficient functionality / web wrapper
5. **2.1-a** — Missing demo account for review
6. **3.1.1-iap** — Digital goods not using Apple IAP
7. **3.1.1-restore** — Missing "Restore Purchases" button
8. **5.1.1-v-delete** — No in-app account deletion
9. **2.3.7-keywords** — Prohibited words in metadata ("free", "best", "#1")
10. **2.3.3** — Screenshots don't show actual app usage
11. **5.1.2-i** — Missing App Tracking Transparency
12. **4.8** — Missing Sign in with Apple when third-party login exists
13. **2.3.6** — Incorrect age rating
14. **1.2** — UGC app missing moderation/reporting/blocking
15. **2.5.5** — App doesn't work on IPv6-only networks
16. **3.1.2-disclosure** — Unclear subscription terms
17. **2.3.10** — References to other platforms in metadata
18. **5.2.1** — Unauthorized third-party IP usage
19. **4.1** — Copycat or impersonation
20. **2.5.1** — Private API usage
```

**Action:** Replace with updated ranking:
```markdown
## Quick Reference: Top 20 Rejection Triggers (2026)

These are the guidelines most commonly causing rejection in 2026 — audit these first. **Ranking has shifted:** account deletion enforcement increased significantly; privacy policy enforcement remains #1.

1. **5.1.1-i** — Missing or inaccessible privacy policy ⚠️ CRITICAL
2. **2.1-a** — App crashes, broken features, incomplete metadata
3. **5.1.1-v-delete** — No in-app account deletion ⚠️ HEAVILY ENFORCED (moved up from #8)
4. **2.3** — Misleading metadata (description doesn't match app)
5. **4.2** — Insufficient functionality / web wrapper
6. **3.1.1-iap** — Digital goods not using Apple IAP
7. **3.1.1-restore** — Missing "Restore Purchases" button
8. **2.3.3** — Screenshots don't show actual app usage
9. **5.1.2-i** — Missing App Tracking Transparency
10. **4.8** — Missing Sign in with Apple when third-party login exists
11. **2.3.6** — Incorrect age rating
12. **2.3.7-keywords** — Prohibited words in metadata ("free", "best", "#1")
13. **1.2** — UGC app missing moderation/reporting/blocking
14. **5.2.1** — Unauthorized third-party IP usage
15. **3.1.2-disclosure** — Unclear subscription terms
16. **2.5.1** — Private API usage
17. **2.3.10** — References to other platforms in metadata
18. **4.1** — Copycat or impersonation
19. **2.5.5** — App doesn't work on IPv6-only networks
20. **5.1.1-v-social** — Social login without Sign in with Apple OR non-login guest option

**Key Changes from 2024:**
- Account deletion moved to #3 (from #8) — enforcement increased significantly in 2024-2026
- Privacy policy (already #1) — enforcement stricter; "accessible" now means easier access required
- Metadata issues rank higher — Apple's focus on developer accuracy has increased
```

**Estimated changes:** Significant reordering and additions (~15 lines)

---

## File: `README.md`

### Optional: Update Highlights Section

**Current:**
```markdown
- Checks your app against all 5 sections of Apple's Review Guidelines (Safety, Performance, Business, Design, Legal)
- Prioritizes the Top 20 most common rejection triggers first
- Provides per-guideline verdicts: PASS, FAIL, WARNING, or N/A
- Gives specific fix suggestions with file paths and code references
- Generates an actionable pre-submission checklist
```

**Action (optional):** Could add:
```markdown
- Checks against 150+ guidelines organized in 5 sections (Safety, Performance, Business, Design, Legal + new Alternative Distribution)
- Prioritizes top rejection triggers from 2026 enforcement patterns
- Includes emerging categories: mini-apps/streaming/chatbots, health research protocols, EU Notarization, cryptocurrency licensing
- Per-guideline verdicts: PASS, FAIL, WARNING, or N/A
- Provides specific fix suggestions with file paths and code references
- Generates actionable pre-submission checklist
```

**Estimated changes:** ~2 lines rewritten (optional)

---

## Summary of Changes by File

| File | Sections to Update | Priority | Est. Lines | Complexity |
|------|-------------------|----------|-----------|------------|
| `guidelines.md` | 1.3, 2.5.16-17, 3.1.5, 4.7 (major), 5.1.1-ii, 5.1.1-v-delete, 5.1.3, +Section 6 | HIGH | ~100 lines | High |
| `guidelines.md` | Top 20 Rejection Triggers | HIGH | ~15 lines | Medium |
| `SKILL.md` | Phase 2 note about Top 20 | MEDIUM | ~1 line | Low |
| `README.md` | Highlights section | LOW | ~2 lines | Low |

---

## Testing Plan

After making updates:

1. **Regression Test:** Run skill against a simple iOS app project to ensure no broken references
2. **Coverage Test:** Create test case for Kids app using COPPA rules (new section)
3. **Coverage Test:** Create test case for mini-app host (new 4.7 details)
4. **Coverage Test:** Create test case for health research app (new 5.1.3 details)
5. **Metadata Test:** Verify Top 20 rejections are caught in priority order
6. **Verification:** Check that all new guideline references are correctly linked

---

## Estimated Total Implementation Time

- **Guidelines.md updates:** 2-3 hours (research + careful writing)
- **Testing:** 1-2 hours (multiple test cases)
- **README/SKILL.md updates:** 30 minutes
- **Review & refinement:** 30 minutes
- **Total:** 4-6 hours for complete, tested implementation

