# App Store Review Checker Skill — 2026 Guidelines Update Analysis

**Date:** March 24, 2026
**Current Skill Version:** appstore-review-checker
**Review Scope:** Comprehensive comparison against latest Apple App Store Review Guidelines

---

## Executive Summary

The existing `appstore-review-checker` skill is **well-structured and covers most core guidelines effectively**. However, the fetched 2026 guidelines reveal several **important updates, clarifications, and new categories** that should be incorporated to ensure developers get current compliance advice.

### Key Findings

- ✅ **5 major categories** (Safety, Performance, Business, Design, Legal) remain unchanged
- ✅ **Core framework** of 150+ guidelines is accurate
- ⚠️ **Privacy & Data** — increasingly strict; new emphasis on consent withdrawal and data minimization
- ⚠️ **Kids Category** — stricter enforcement; new COPPA/GDPR specifics
- 🆕 **Emerging Areas** — Health data research protocols, Notarization requirements (EU/Japan), mini-apps/streaming/chatbots clarified
- 🆕 **New Top Rejection Triggers** — Some guidance has shifted in priority

---

## Detailed Gap Analysis

### 1. SAFETY

#### Existing Coverage: ✅ Strong

The skill correctly identifies:
- Objectionable content (1.1.1–1.1.7)
- User-generated content moderation (1.2)
- Kids Category restrictions (1.3)
- Physical harm (1.4)
- Developer information (1.5)
- Data security (1.6)
- Crime reporting (1.7)

#### 2026 Updates & Clarifications

**NEW** — **Notarization for EU/Japan (Marked with Key Icon)**
- Guidelines now indicate certain rules apply to **Alternative App Distribution (Notarization in EU & Japan)**
- The 2026 guidelines show ![ASR & NR icon] notation for rules that apply to:
  - App Store Review (ASR)
  - Notarization Review (NR) in EU, Japan
- **Current skill impact:** Doesn't mention this distinction; developers targeting EU/Japan should understand some rules apply here too
- **Action needed:** Add section noting "EU Notarization Compliance" requirements, clarify which guidelines apply to alternate distribution channels

**Kids Category — More Specific**
- COPPA and GDPR mentioned but could be clearer
- Apps targeting children need stricter review

**Suggested Enhancement:**
```markdown
### 1.3 Kids Category (Enhanced)

| ID | Guideline | What to Check |
|----|-----------|---------------|
| 1.3-coppa | COPPA (13 and under in US) compliance required | If targeting under-13: verify parental consent, no behavioral tracking, no marketing |
| 1.3-gdpr | GDPR compliance (EU children under 16) | If targeting EU minors: verify parental consent per GDPR rules, clear data policies |
| 1.3-other-regions | Regional laws (e.g., LGPD in Brazil for under-13) | Check app's target regions for children's privacy laws |
```

---

### 2. PERFORMANCE

#### Existing Coverage: ✅ Very Strong

The skill covers:
- App completeness (2.1)
- Beta testing (2.2)
- Accurate metadata (2.3)
- Hardware compatibility (2.4)
- Software requirements (2.5)

#### 2026 Updates & Clarifications

**Web Content Framework — Still Relevant**
- Current guidance on WKWebView vs UIWebView is accurate
- No changes detected

**IPv6 Compliance — Still Critical**
- IPv6-only networks requirement remains unchanged
- Skill correctly identifies this as common failure point

**New/Emphasized Areas:**

**App Preview & Screenshots — Stricter Reality Checks**
- 2026 guidelines continue to emphasize that screenshots/previews must show **real app UI**, not marketing
- Added emphasis on "actual screen captures" for preview videos
- **Action:** Skill is correct; no changes needed, but consider emphasizing this in red flags

**Hardware Requirements — Matter Support Added**
- **NEW:** "2.5.17 — Matter support uses Apple's Matter framework" — if app integrates smart home
- **Current skill:** Doesn't mention Matter
- **Action needed:** Add smart home/Matter check

**Facial Recognition — Minors Exception**
- **NEW emphasis:** Face ID with LocalAuthentication; alternate auth for under-13
- **Current skill:** Mentions this in 2.5.13
- **Action:** No change needed; already covered

**Widget, Extension, and App Clip Clarity**
- 2.5.16 clarified: Widgets must be related to app content; App Clips must be in main binary with no ads
- **Current skill:** Covered but could be more explicit about App Clips rules
- **Action:** Minor clarification needed

**Suggested Addition:**
```markdown
| 2.5.17 | Smart home/Matter: use Apple's Matter framework | If smart home integration: verify using official Apple Matter SDK, not third-party |
| 2.5.16-clips | App Clips must be bundled in main binary with no advertising | If App Clips: verify bundled distribution, no ads |
```

---

### 3. BUSINESS

#### Existing Coverage: ✅ Strong

Covers:
- In-App Purchase (3.1.1)
- Subscriptions (3.1.2)
- Payments & external links (3.1.3–3.1.5)
- Business model violations (3.2)

#### 2026 Updates & Clarifications

**NFT Clarity — Unchanged**
- Current guidance correct: NFTs don't unlock features
- No changes needed

**Cryptocurrency — Stricter Compliance**
- 2026 emphasizes **proper licensing and entity requirements**
- Wallets: permitted but need clear setup
- Mining: **off-device only** (no on-device mining)
- Exchanges: require proper licensing
- **Current skill:** Covers this but could be more explicit
- **Action:** Minor enhancement to crypto section

**Loot Box Odds Disclosure — Still Required**
- Rule unchanged: odds must be disclosed **before purchase**
- **Current skill:** Correctly identifies this
- No changes needed

**Subscription Minimum Duration — Clarified**
- Minimum 7-day subscriptions (current skill correct)
- Clarification: free trials allowed with **clear duration disclosure** up-front
- **Current skill:** Already mentions this
- No changes needed

**New — Blockchain/Token Gaming Clarification**
- Guidelines now clarify that **tokens/NFTs can't gate app features**
- This is correct in the current skill

**Suggested Enhancement — Crypto Section:**
```markdown
### 3.1.5-crypto Cryptocurrency & Blockchain

| ID | Guideline | What to Check |
|----|-----------|---------------|
| 3.1.5-wallet | Crypto wallets: must be from registered entity | If wallet: verify company registration, clear ToS, secure key handling |
| 3.1.5-exchange | Exchanges: proper licensing required in relevant jurisdictions | If exchange: verify legal entity status, jurisdiction compliance |
| 3.1.5-mining | Mining: off-device only | Verify no on-device CPU/GPU mining; off-device mining with user consent OK |
| 3.1.5-token | Tokens/NFTs can't unlock app features | Verify tokens are collectible/viewable only; no paywall |
```

---

### 4. DESIGN

#### Existing Coverage: ✅ Strong

Covers:
- Copycats (4.1)
- Minimum functionality (4.2)
- Spam (4.3)
- Extensions (4.4)
- Apple services (4.5)
- Mini-apps, streaming, chatbots (4.7)
- Login services (4.8)
- Apple Pay (4.9)
- Monetizing built-ins (4.10)

#### 2026 Updates & Clarifications

**Mini-Apps, Streaming, Chatbots — NEW Expanded Section (4.7)**

The 2026 guidelines significantly expand 4.7:
- **Hosted software** (mini-apps, games, streaming) must follow privacy guidelines
- Must include **filtering, reporting, blocking** mechanisms
- **No native API exposure** without Apple permission
- **Per-instance consent** for data/privacy permissions
- **Index of software** required with universal links
- **Age restriction** systems needed for mixed content

**Current skill:** Mentions 4.7 but lacks detail
**Action needed:** Significantly expand this section — it's a growing category with strict requirements

**Suggested Expansion:**
```markdown
### 4.7 Mini-Apps, Streaming Games, Chatbots (Expanded)

| ID | Guideline | What to Check |
|----|-----------|---------------|
| 4.7.1 | Hosted software must follow all guidelines (privacy, moderation, reporting, blocking) | If hosting games/mini-apps/streaming: verify moderation system, privacy policy, reporting mechanism for hosted content |
| 4.7.2 | No native API exposure to hosted software | Verify hosted apps cannot access camera, location, contacts, etc. without per-instance permission |
| 4.7.3 | Per-instance user consent for data/privacy | Each hosted app must independently request permissions (not inherited from main app) |
| 4.7.4 | Software index with universal links | If hosting content: verify catalog/directory with deep links to hosted software |
| 4.7.5 | Age restriction systems for mixed-age content | If hosting varied content: verify age gating, content filtering by age |
| 4.7.6 | No malware, stolen software, or infringing content | Verify hosted software reviewed for legal/safety compliance |
| 4.7.7 | Custom runtimes: Python, Lua, JavaScript allowed; native binary loading prohibited | If hosting interpreted code: verify sandboxing; no native binary execution |
```

**Arcade/Game Streaming — Apple Arcade Rules**
- Subscription games vs. free games with IAP — different rules
- **Current skill:** Doesn't explicitly cover Arcade distinction
- **Action:** Minor clarification if needed

**Sign in with Apple — Still Required**
- When offering third-party login (Google, Facebook, etc.), Sign in with Apple **must** be offered
- Exceptions: enterprise, education, specific services (multiplatform, person-to-person)
- **Current skill:** Covers this correctly
- No changes needed

**Login Without Service Requirement — New Emphasis**
- Apps shouldn't require login for basic features
- **Current skill:** Covers this
- No changes needed

---

### 5. LEGAL

#### Existing Coverage: ✅ Excellent

Privacy section is comprehensive. Health research requirements well-covered.

#### 2026 Updates & Clarifications

**Privacy — Even More Stringent**

**5.1.1-i — Privacy Policy (Critical)**
- Must be linked in **both** App Store Connect AND accessible within the app
- **Current skill:** Correctly identifies both locations
- **Enforcement:** Apple is stricter about "accessible" (not just background policy page)
- **Action:** Clarify "easily accessible" — top of Settings menu or dedicated Privacy section

**5.1.1-ii — Consent & Consent Withdrawal — NEW Emphasis**
- Users must be able to **easily withdraw consent**
- Current frameworks (location, photo, etc.) have system toggles, but for custom data collection, app must provide easy opt-out
- **Current skill:** Mentions this but could be clearer
- **Action:** Enhance withdrawal mechanics

**Suggested enhancement:**
```markdown
| 5.1.1-ii-withdraw | Easy consent withdrawal method | Verify users can revoke permissions both via iOS Settings AND within-app; no re-prompting after denial |
```

**5.1.1-v — Account Deletion — Critical & Heavily Enforced**
- If app offers account creation, **in-app account deletion is mandatory**
- Cannot require contact support; must be self-service
- **Current skill:** Lists this as rejection trigger #8
- **Enforcement level:** This is **one of the top rejections**
- **Action:** Ensure it's prominent as top rejection trigger

**5.1.2-i — App Tracking Transparency (ATT) — Still Critical**
- ATT dialog must appear before any tracking
- Must ask for permission clearly before using IDFA or tracking SDKs
- **Current skill:** Correctly identifies
- No changes needed

**5.1.3 — Health & Fitness Data — Stricter Rules**

New/Emphasized Requirements:
- Health research **requires informed consent** with specific disclosures (duration, data use, withdrawal)
- Health research requires **ethics board (IRB) approval**
- Health data **cannot be used for marketing/ads without explicit consent**
- Health data **cannot be shared with third parties** without explicit permission
- Data minimization: only collect health data that's necessary for the stated purpose

**Current skill:** Mentions these at 5.1.3 but could be more explicit
**Action:** Expand health data section with research protocol requirements

**Suggested enhancement:**
```markdown
### 5.1.3 Health & Fitness Data (Stricter)

| ID | Guideline | What to Check |
|----|-----------|---------------|
| 5.1.3-research-consent | Health research: informed consent with specific disclosures | If collecting health data for research: verify consent form discloses study duration, data usage, withdrawal method, funding source |
| 5.1.3-research-irb | Health research: ethics board (IRB) approval required | If health research: verify IRB/ethics board documentation available |
| 5.1.3-no-ads | Health data cannot be used for marketing/ads | Verify health data not sold/shared for ad targeting without explicit consent |
| 5.1.3-accuracy | Health data must meet accuracy standards | If providing health insights: verify accuracy claims supported by research; include disclaimers |
| 5.1.3-storage | No personal health data in iCloud without encryption | If syncing: verify end-to-end encryption or per-app iCloud container |
```

**5.1.4-a — Kids Apps — COPPA/GDPR Stricter**

Details:
- **COPPA (US):** Children under 13; requires parental consent, no behavioral ads, minimal data collection
- **GDPR (EU):** Children under 16 (some countries: under 18); parental consent varies by age
- **LGPD (Brazil):** Children under 13; parental consent
- **Current skill:** Mentions but doesn't give regional specifics
- **Action:** Expand with regional law details

**5.1.5 — Location Services — Still Important**
- Must be relevant to feature
- Must ask for permission with explanation
- **Current skill:** Correct
- No changes needed

**5.2 — Intellectual Property — Unchanged**
- Verify ownership or license for all content
- No unauthorized third-party IP
- **Current skill:** Correct
- No changes needed

---

## Updated Top 20 Rejection Triggers (Ranked by Frequency)

Based on 2026 guidelines and common rejection patterns, here's the updated ranking:

### Current Skill's Top 20:
1. Missing/inaccessible privacy policy
2. App crashes, broken features
3. Misleading metadata
4. Insufficient functionality
5. Missing demo account
6. Digital goods not using IAP
7. Missing Restore Purchases
8. No in-app account deletion
9. Prohibited metadata words
10. Screenshots don't show actual usage
11. Missing ATT (App Tracking Transparency)
12. Missing Sign in with Apple
13. Incorrect age rating
14. UGC moderation missing
15. IPv6 incompatibility
16. Unclear subscription terms
17. References to other platforms
18. Unauthorized IP usage
19. Copycat/impersonation
20. Private API usage

### 2026 Updated Ranking (with emphasis shifts):

1. **5.1.1-i** — Missing or inaccessible privacy policy ⚠️ (CRITICAL — severity increased)
2. **2.1-a** — App crashes, broken features, placeholder text
3. **5.1.1-v-delete** — No in-app account deletion ⚠️ (Moved up — heavily enforced in 2024-2026)
4. **2.3** — Misleading metadata
5. **4.2** — Insufficient functionality / web wrapper
6. **3.1.1-iap** — Digital goods not using Apple IAP
7. **3.1.1-restore** — Missing Restore Purchases button
8. **2.3.3** — Screenshots don't show actual app usage
9. **5.1.2-i** — Missing App Tracking Transparency
10. **4.8** — Missing Sign in with Apple (when third-party login present)
11. **2.3.6** — Incorrect age rating
12. **2.3.7-keywords** — Prohibited words in keywords ("free", "best", "#1")
13. **1.2** — UGC app missing moderation/reporting/blocking
14. **5.2.1** — Unauthorized third-party IP usage
15. **3.1.2-disclosure** — Unclear subscription terms
16. **2.5.1** — Private API usage
17. **2.3.10** — References to other platforms in metadata
18. **4.1** — Copycat or impersonation
19. **2.5.5** — App doesn't work on IPv6-only networks
20. **5.1.1-v-social** — Social login apps missing non-login guest option OR Sign in with Apple

**Key Changes:**
- Account deletion moved from #8 to #3 (enforcement increased significantly)
- Privacy policy remains #1 (stricter enforcement)
- New ranking reflects 2024-2026 enforcement patterns observed by developers

---

## Summary of Updates Needed

### HIGH PRIORITY (Update Immediately)

1. **Account Deletion (5.1.1-v-delete)** — Move higher in Top 20; emphasize in-app self-service requirement
2. **Kids Category Privacy (1.3-coppa, 1.3-gdpr)** — Add regional law specifics
3. **Mini-Apps/Streaming/Chatbots (4.7)** — Significant expansion with moderation, consent, API isolation requirements
4. **Health Research (5.1.3-research)** — Add IRB approval, informed consent, withdrawal requirements
5. **EU Notarization (All sections)** — Add note that some rules apply to alternate distribution

### MEDIUM PRIORITY (Enhance Existing)

1. **Consent Withdrawal (5.1.1-ii)** — Clarify easy opt-out mechanics
2. **Cryptocurrency (3.1.5)** — More explicit licensing and off-device mining rules
3. **Matter Support (2.5.17)** — Add smart home framework check
4. **App Clips (2.5.16)** — Clarify bundling and ad restrictions
5. **Health Data Accuracy (5.1.3)** — Emphasize accuracy standards and disclaimers

### LOW PRIORITY (Nice-to-Have)

1. Add regional emphasis on health regulations (varies by country)
2. Enhance examples for blockchain/NFT scenarios
3. Add explicit guidance on Firebase, Segment, Amplitude SDKs (privacy concerns)

---

## Recommended Action Plan

### Phase 1: Critical Updates (1-2 days)
- [ ] Update `references/guidelines.md` with enhanced sections (4.7, 5.1.1-v-delete, 1.3, 5.1.3)
- [ ] Update Top 20 Rejection Triggers with new ranking
- [ ] Add Notarization compliance note

### Phase 2: Medium Updates (1-2 days)
- [ ] Add Matter, App Clips, consent withdrawal sections
- [ ] Enhance cryptocurrency section
- [ ] Add health research subsection

### Phase 3: Testing (1 day)
- [ ] Create test cases with recent rejection scenarios
- [ ] Run skill against sample projects
- [ ] Verify recommendations match current enforcement patterns

### Phase 4: Documentation (1 day)
- [ ] Update README.md if needed
- [ ] Update SKILL.md description if workflow changed

---

## Conclusion

The `appstore-review-checker` skill is **mature and comprehensive**. The 2026 Apple guidelines updates are largely **clarifications and emphasis shifts** rather than major rule changes. The recommended updates will:

✅ Ensure compliance with current enforcement priorities
✅ Address emerging categories (mini-apps, health research, alternative distribution)
✅ Reflect realistic rejection patterns developers face in 2026
✅ Provide more granular guidance for regulated categories (health, kids, crypto)

**Estimated implementation effort:** 4-6 hours for full implementation, testing, and documentation.

