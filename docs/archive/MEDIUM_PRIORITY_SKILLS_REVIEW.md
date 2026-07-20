# MEDIUM Priority Skills Review
> Comprehensive analysis of 10 MEDIUM-priority skills identified for subagent adoption

**Date:** 2026-03-25
**Reviewer:** Claude Code
**Source:** SUBAGENT_ADOPTION_PLAN.md

---

## Overview

| Skill | Score | Pattern | Status | Ready? | Recommendation |
|-------|-------|---------|--------|--------|---|
| **dont-make-me-think** | 4/5 | Review Loop (C) | ✅ Complete | Yes | Start after HIGH priority pilot |
| **readme-to-landing-page** | 4/5 | Review Loop (C) | ✅ Complete | Yes | Start after HIGH priority pilot |
| **cli-builder** | 4/5 | Explorer+Executor (A) | ✅ Complete | Yes | Parallel with theme-transformer |
| **theme-transformer** | 4/5 | Explorer+Executor (A) | ✅ Complete | Yes | Parallel with cli-builder |
| **code-optimizer** | 3/5 | Explorer+Executor (A) | ✅ Complete | Yes | After Explorer+Executor pattern stabilizes |
| **test-coverage** | 3/5 | Explorer+Parallel (A+B) | ✅ Complete | Yes | After Parallel pattern validated |
| **prd-generator** | 3/5 | Pipeline+Review (E+C) | ✅ Complete | Partial | Blocked on idea-validator integration |
| **install-script-generator** | 3/5 | Pipeline (E) | ✅ Complete | Yes | Stable, straightforward pattern |
| **ollama-optimizer** | 3/5 | Explorer+Executor (A) | ✅ Complete | Yes | Good reference for system profiling |
| **skill-creator** | 5 (existing) | Refactor | 🔄 Complex | Partial | Needs careful refactoring—already has subagents |

---

## Detailed Analysis by Skill

### 1. dont-make-me-think (Score: 4/5)
**Pattern:** Review Loop (C) — Creator + Independent Reviewer
**Current State:** SKILL.md (135 lines) + references/krug-principles.md
**Complexity:** Medium

#### What would subagents do?
- **ui-analyst**: Receive screenshot/URL, run Krug checklist, return structured findings (10 lenses)
- **report-writer**: Take analyst findings, format into scannable markdown with tables/diagrams
- **fixer**: Suggest specific UI redesigns based on findings

#### Why beneficial?
- Large screenshots require attention; analyzer can focus purely on inspection
- Report writing has specific style requirements (scannable, no fluff); separate agent keeps it consistent
- Fresh reviewer can validate findings without bias from initial analysis

#### Implementation Priority: **Medium-High**
- ✅ Skill is complete and stable
- ✅ Pattern is proven (Review Loop used in excalidraw, drawio)
- ✅ Clear separation of concerns
- ⚠️ Depends on `/browse` skill for URLs—ensure compatibility

#### Recommended next step:
Write agents/ui-analyst.md first, test on 2-3 screenshots, validate checklist structure.

---

### 2. readme-to-landing-page (Score: 4/5)
**Pattern:** Review Loop (C) — Writer + Reviewer
**Current State:** SKILL.md (200+ lines) + multiple references
**Complexity:** High (copywriting-heavy)

#### What would subagents do?
- **researcher**: Read project/README files, extract brand story, competitive positioning
- **writer**: Generate landing-page-structured markdown (hero → problem → solution → proof → CTA)
- **reviewer**: Validate anti-slop rules (banned phrases, no emoji, pruned prose), check conversion flow

#### Why beneficial?
- Reader phase: large README + project files → use researcher subagent to avoid context bloat
- Writing phase: markdown generation is straightforward but voluminous; separate agent keeps clean output
- Review phase: fresh reviewer catches "slop" patterns without bias (writer is already committed to phrasing choices)

#### Implementation Priority: **Medium-High**
- ✅ Skill is proven (2.0.0 with test iterations)
- ✅ Anti-slop rules are explicit and grading-friendly
- ✅ Clear 3-phase pipeline (research → write → review)
- ⚠️ High copy quality needs fresh-eye validation (this is why Review Loop is essential)

#### Recommended next step:
Design researcher.md to extract story elements, writer.md to apply copywriting frameworks (PAS, AIDA, StoryBrand), reviewer.md to validate output against anti-slop checklist.

---

### 3. cli-builder (Score: 4/5)
**Pattern:** Explorer+Executor (A) — Analyzer + Implementer
**Current State:** SKILL.md (95+ lines, substantial workflow) + references/cli-libraries.md, references/testing-patterns.md
**Complexity:** High (5-step approval-gated workflow)

#### What would subagents do?
- **analyzer**: Read project structure, language, existing modules → recommend CLI framework + design patterns
- **implementer**: Generate CLI code scaffold using recommended framework + tests
- **reviewer**: Validate scaffold against 5-step workflow requirements (design correctness, test coverage)

#### Why beneficial?
- Analyzer phase: reads project files to infer language/framework; can be done independently
- Executor phase: code generation is substantial; separate context keeps it clean
- Reviewer phase: fresh validation that design matches user approval (Step 3)

#### Implementation Priority: **High**
- ✅ Skill is mature (v1.0.0, approval-gated)
- ✅ Clear 5-step workflow maps to subagents naturally
- ✅ References are well-organized (cli-libraries, testing-patterns)
- ✅ Mandatory repo-sync guardrail already in place
- ⚠️ Must preserve user approval gates (Step 3: "Design" requires user sign-off before exec)

#### Recommended next step:
Implement as part of Explorer+Executor cohort. Main agent orchestrates approval gates; subagents handle analysis, implementation, review.

---

### 4. theme-transformer (Score: 4/5)
**Pattern:** Explorer+Executor (A) — Style Auditor + Theme Executor
**Current State:** SKILL.md (85+ lines, 4-step workflow) + references/theme-tokens.md, references/neon-command-center.md
**Complexity:** High (file transformation + style coherence)

#### What would subagents do?
- **style-auditor**: Analyze current UI (code + screenshots), produce style inventory (colors, fonts, layouts)
- **theme-executor**: Apply theme tokens per references, transform CSS/styling files
- **accessibility-checker**: Validate color contrast, readability after theme application

#### Why beneficial?
- Audit phase: reads many component files; auditor can build comprehensive style map
- Execution phase: file transforms are heavy; separate agent keeps clean diffs
- Validation phase: fresh reviewer ensures accessibility standards met (WCAG contrast, etc.)

#### Implementation Priority: **High**
- ✅ Skill is mature and stable
- ✅ 4-step workflow clearly maps to phases
- ✅ Mandatory repo-sync guardrail already in place
- ✅ References are specific and usable
- ⚠️ Accessibility validation is critical—must not skip

#### Recommended next step:
Pair with cli-builder as part of Explorer+Executor cohort. Both follow similar pattern with analyzer → executor → reviewer flow.

---

### 5. code-optimizer (Score: 3/5)
**Pattern:** Explorer+Executor (A) — Analyzer + Fixer
**Current State:** SKILL.md (60+ lines) + clear priority order
**Complexity:** Medium (analysis + targeted fixes)

#### What would subagents do?
- **analyzer**: Scan code, identify issues (bottlenecks, memory leaks, caching opportunities) → return structured JSON
- **fixer**: Apply targeted optimizations per issue category

#### Why beneficial?
- Analysis phase: reads full codebase, applies 5 priority checks; subagent can build comprehensive issue map
- Fixing phase: per-issue fixes can be done independently (fixer doesn't need to re-analyze)

#### Implementation Priority: **Medium**
- ✅ Skill is stable (v1.2.0)
- ✅ Priority order is clear and objective
- ✅ Mandatory repo-sync in place
- ⚠️ Lower score (3/5) suggests modest subagent benefit
- ⚠️ Context-light skill; parallelization won't yield huge speedup

#### Recommended next step:
Implement after higher-priority Explorer+Executor skills (cli-builder, theme-transformer). Simple analyzer+fixer pattern is good for learning.

---

### 6. test-coverage (Score: 3/5)
**Pattern:** Explorer+Parallel (A+B) — Coverage Analyzer + Parallel Test Writers
**Current State:** SKILL.md (50+ lines, framework-adaptive) + framework-specific configs
**Complexity:** Medium (framework detection + parallel test generation)

#### What would subagents do?
- **coverage-analyzer**: Run coverage report per framework, identify untested branches → return JSON of gaps
- **test-writer**: Generate tests for one module's gaps (spawned in parallel, one per module)
- **assembler**: Merge all test files back into project structure

#### Why beneficial?
- Analyzer phase: runs coverage tool, parses output; subagent can focus on report interpretation
- Test generation: **parallelizable by module**; each module's tests are independent → ~2-4x speedup
- Assembly phase: ensures all tests integrate correctly without conflicts

#### Implementation Priority: **Medium-Low**
- ✅ Skill is mature (v1.2.0)
- ⚠️ Score of 3/5 indicates modest benefit
- ⚠️ Test quality depends on coverage analysis being accurate
- ⚠️ Parallel workers require care to avoid duplicate/conflicting tests

#### Recommended next step:
Implement after parallel pattern is validated elsewhere. Good candidate for learning parallel architecture.

---

### 7. prd-generator (Score: 3/5)
**Pattern:** Pipeline+Review (E+C) — Context Extractor → Writer → Reviewer
**Current State:** SKILL.md (80+ lines, input-adaptive) + references/prd-template.md
**Complexity:** High (multi-phase workflow, idea validation dependency)

#### What would subagents do?
- **context-extractor**: Read idea.md + validate.md → extract requirements, constraints, success criteria
- **prd-writer**: Generate full PRD.md per template, applying structured sections
- **prd-reviewer**: Validate completeness, clarity, requirement traceability

#### Why beneficial?
- Extraction: reads 2+ input files, structures findings; separate agent keeps clean
- Writing: PRD generation is voluminous; separate context avoids mixing input parsing + output generation
- Review: fresh validator catches gaps in requirement clarity

#### Implementation Priority: **Medium (Blocked)**
- ✅ Skill is mature (v1.2.2)
- ✅ Clear pipeline pattern
- ⚠️ **Blocked on idea-validator integration**: current skill expects idea.md + validate.md but those files are created by idea-validator skill
- ⚠️ Dependency chain: idea-validator → prd-generator → tasks-generator → system-design
- ⚠️ Must coordinate with release of other skills in chain

#### Recommended next step:
Implement after validating pipeline pattern elsewhere. Ensure integration with idea-validator is tested (shared marker files, path detection).

---

### 8. install-script-generator (Score: 3/5)
**Pattern:** Pipeline (E) — Analyzer → Planner → Generator → Validator
**Current State:** SKILL.md (90+ lines, 4-phase approach) + clear cross-platform design
**Complexity:** High (shell script generation, platform-specific logic)

#### What would subagents do?
- **env-analyzer**: Detect OS, architecture, package managers → return system profile JSON
- **script-writer**: Generate install.sh + optionally install.ps1 from profile
- **script-validator**: Test script against target environment requirements

#### Why beneficial?
- Analysis: system detection is deterministic; subagent can gather all facts
- Writing: shell script generation is complex; separate context keeps it focused
- Validation: fresh agent can test script logic without bias from generation decisions

#### Implementation Priority: **Medium**
- ✅ Skill is mature (v2.0.0)
- ✅ Clear 4-phase pipeline
- ✅ Mandatory repo-sync in place
- ✅ Good candidate for Pipeline pattern validation
- ⚠️ Score of 3/5 suggests modest parallel benefit
- ⚠️ Stages are strictly sequential (analyzer → planner → gen → validator)

#### Recommended next step:
Implement as learning example for Pipeline pattern. Straightforward phase separation, good for testing subagent coordination.

---

### 9. ollama-optimizer (Score: 3/5)
**Pattern:** Explorer+Executor (A) — System Analyzer + Guide Generator
**Current State:** SKILL.md (70+ lines, detection + recommendation phases) + references/ (vram, env vars, platform-specific)
**Complexity:** Medium (system profiling + hardware-specific tuning)

#### What would subagents do?
- **system-analyzer**: Run detection scripts, parse JSON output, profile hardware (GPU, RAM, CPU) → return structured analysis
- **guide-generator**: Apply profiling to generate Ollama configuration recommendations + tuning guide

#### Why beneficial?
- Analysis: system detection involves running external scripts + parsing; subagent can handle all I/O
- Generation: recommendations are hardware-dependent; separate agent can focus on tuning rules

#### Implementation Priority: **Medium**
- ✅ Skill is mature (v1.0.1)
- ✅ Clear 2-phase workflow (detection → recommendation)
- ✅ Good reference for system profiling patterns
- ⚠️ Score of 3/5 suggests modest benefit
- ⚠️ Detection depends on local system state; subagent must run in same environment

#### Recommended next step:
Good reference implementation for system profiling. Could be studied before implementing system-design (which also profiles PRD requirements).

---

### 10. skill-creator (Score: 5 — Existing, Refactoring)
**Pattern:** Complex multi-phase orchestrator (already uses subagents)
**Current State:** SKILL.md (596 lines — **exceeds 500-line recommendation**)
**Complexity:** Max (full skill development lifecycle)

#### Current architecture:
- Already delegates to subagents: `agents/grader.md`, `agents/analyzer.md`, `agents/comparator.md`
- Main SKILL.md is **bloated** with implementation details that should be in agent files

#### What refactoring would do:
- Extract executor-phase logic (test spawning, eval coordination) into `agents/executor.md`
- Move test case generation into `agents/test-designer.md`
- Keep SKILL.md as pure orchestration (< 300 lines)
- Clarify when each subagent is spawned and what it receives

#### Why beneficial?
- **Current problem**: SKILL.md is hard to navigate at 596 lines; readers get lost in detail
- **Refactoring**: Extract middle layers → main agent becomes pure conductor
- **Clarity**: each phase gets dedicated subagent file with focused prompt

#### Implementation Priority: **Lower (Refactoring)**
- ✅ Skill is highly functional and used in production
- ✅ Already has subagent pattern; just needs extraction
- ⚠️ **Risk of regression**: must preserve all 596 lines of logic, just reorganize
- ⚠️ Refactoring should only proceed after HIGH-priority skills are complete
- ⚠️ Test thoroughly—this skill is critical path for other developments

#### Recommended next step:
**After HIGH priority skills pilot completes (Phase 1 of implementation)**, extract executor.md and test-designer.md. Validate that eval loop still works identically to before.

---

## Implementation Roadmap

### Phase 1: Review Loop Pattern (Start Now)
Both Review Loop skills are well-positioned to start immediately after HIGH-priority pilot:

1. **dont-make-me-think**
   - Create agents/ui-analyst.md, agents/report-writer.md, agents/fixer.md
   - Test on 3 UI review scenarios
   - Estimated effort: 1-2 days

2. **readme-to-landing-page**
   - Create agents/researcher.md, agents/writer.md, agents/reviewer.md
   - Test on 3 project READMEs
   - Estimated effort: 2-3 days

**Timeline:** Weeks 1-2 (after HIGH priority validation)

---

### Phase 2: Explorer+Executor Pattern (Weeks 2-3)
Parallel implementation of style/code analyzers:

3. **cli-builder** + **theme-transformer** (parallel)
   - Both follow analyzer → implementer → reviewer pattern
   - Shared testing approach
   - Estimated effort: 3-4 days each

4. **code-optimizer**
   - Simpler analyzer+fixer variant
   - Good learning for simpler Explorer+Executor
   - Estimated effort: 1-2 days

**Timeline:** Weeks 2-3 (parallel with review loop polish)

---

### Phase 3: Pipeline & Parallel Patterns (Week 4)
Stable patterns validated in earlier phases:

5. **install-script-generator**
   - Clear 4-phase pipeline; straightforward
   - Estimated effort: 1-2 days

6. **test-coverage**
   - First Parallel Workers implementation
   - Test coverage analyzer + parallel test writers
   - Estimated effort: 2-3 days

7. **ollama-optimizer**
   - System profiling reference; modest complexity
   - Estimated effort: 1 day

**Timeline:** Week 4

---

### Phase 4: Complex Pipelines & Refactoring (Week 5)
Once simpler patterns are stable:

8. **prd-generator**
   - Pipeline+Review pattern
   - Requires coordination with idea-validator
   - Estimated effort: 2-3 days

9. **skill-creator (refactor)**
   - Extract executor.md + test-designer.md
   - Validate regression tests pass
   - Estimated effort: 2-3 days

**Timeline:** Week 5

---

## Success Criteria

For each MEDIUM-priority skill adoption, validate:

1. ✅ **Subagents are isolated** — each agent file has complete, focused prompt
2. ✅ **Main agent is pure orchestrator** — no file reading or heavy processing
3. ✅ **Graceful degradation** — skill works without Agent tool (inline fallback)
4. ✅ **Test coverage** — evals run with and without subagents, produce identical results
5. ✅ **Documentation** — README lists all agent files and when they're spawned
6. ✅ **SKILL.md < 500 lines** — if exceeds, move content to agent files or references

---

## Key Dependencies & Risks

### External Dependencies
- **dont-make-me-think**: Requires `/browse` skill for live URL testing
- **readme-to-landing-page**: Depends on markdown rendering (should be straightforward)
- **prd-generator**: Blocks on idea-validator being released first
- **test-coverage**: Depends on project test framework being installed

### Pattern Risks
- **Review Loop**: Fresh reviewers might have different opinion than creator; need validation
- **Parallel Workers**: Test writers must not generate duplicate tests; need merge logic
- **Pipeline**: Stages depend on previous output; data format contracts must be precise

### Quality Assurance
- Run all 10 skills' evals against baseline (no subagents) and with subagents
- Verify identical/better output quality
- Benchmark token usage + latency improvements
- Document any regressions

---

## Recommendations

### Quick Wins (Start Immediately After HIGH Pilot)
1. **dont-make-me-think** — Review Loop is proven pattern; low risk
2. **readme-to-landing-page** — High-value copywriting skill; fresh reviewer essential

### High-Impact Medium Effort
3. **cli-builder** + **theme-transformer** — Run in parallel; pattern reuse
4. **install-script-generator** — Clear pipeline; good learning for pipeline pattern

### Deferred (After Pattern Stabilization)
5. **test-coverage** — Good parallel pattern learning; implement after Phase 2
6. **prd-generator** — Blocked on dependency; schedule after idea-validator
7. **skill-creator** — Refactoring only; low risk but wait until core work done
8. **code-optimizer**, **ollama-optimizer** — Lower-priority; implement if resources allow

### Overall Effort Estimate
- **Total implementation**: 20-25 days across 5 weeks
- **Testing & validation**: 5-7 days
- **Buffer & polish**: 3-5 days
- **Grand total**: ~4-5 weeks for all 10 MEDIUM skills + refactoring

---

## Summary Table

| Priority | Skill | Score | Pattern | Start | Est. Days | Risk |
|----------|-------|-------|---------|-------|-----------|------|
| P1 | dont-make-me-think | 4/5 | Review Loop | Week 1 | 1-2 | Low |
| P1 | readme-to-landing-page | 4/5 | Review Loop | Week 1 | 2-3 | Low |
| P2 | cli-builder | 4/5 | Explorer+Exec | Week 2 | 3-4 | Low |
| P2 | theme-transformer | 4/5 | Explorer+Exec | Week 2 | 3-4 | Low |
| P2 | code-optimizer | 3/5 | Explorer+Exec | Week 2 | 1-2 | Low |
| P3 | install-script-generator | 3/5 | Pipeline | Week 4 | 1-2 | Low |
| P3 | test-coverage | 3/5 | Parallel | Week 4 | 2-3 | Med |
| P3 | ollama-optimizer | 3/5 | Explorer+Exec | Week 4 | 1 | Low |
| P4 | prd-generator | 3/5 | Pipeline+Review | Week 5 | 2-3 | Med |
| P4 | skill-creator (refactor) | 5 | Refactor | Week 5 | 2-3 | Med |

---

**Status**: Ready for implementation. Recommend starting with Phase 1 (Review Loop skills) once HIGH-priority pilot is validated.
