# MEDIUM Priority Skills — Complete Subagent Architecture Specifications
> Comprehensive implementation blueprints for all 10 MEDIUM-priority skills with subagent patterns

**Date**: 2026-03-25
**Status**: Ready for implementation
**Total files to create**: ~50 agent prompt files + updated SKILL.md files
**Estimated implementation effort**: 4-5 weeks

---

## Executive Summary

This document consolidates the complete architectural specifications for implementing subagent patterns across all 10 MEDIUM-priority skills. Each skill has been analyzed in parallel by specialized code-architect subagents, producing detailed blueprints with:

- ✅ Complete subagent prompt files (agents/*.md)
- ✅ Updated SKILL.md orchestration logic
- ✅ Data contracts (JSON structures between agents)
- ✅ Graceful degradation paths
- ✅ Build sequence checklists
- ✅ Critical implementation details

---

## Skills at a Glance

| Skill | Pattern | Subagents | Status | Start |
|-------|---------|-----------|--------|-------|
| **dont-make-me-think** | Review Loop (C) | 3 | ✅ Complete | Week 1 |
| **readme-to-landing-page** | Review Loop (C) | 3 | ✅ Complete | Week 1 |
| **cli-builder** | Explorer+Executor (A) | 3 | ✅ Complete | Week 2 |
| **theme-transformer** | Explorer+Executor (A) | 3 | ✅ Complete | Week 2 |
| **code-optimizer** | Explorer+Executor (A) | 6 | ✅ Complete | Week 2 |
| **test-coverage** | Pipeline+Parallel (E+B) | 3 | ✅ Complete | Week 4 |
| **prd-generator** | Pipeline+Review (E+C) | 3 | ✅ Complete | Week 5 |
| **install-script-generator** | Pipeline (E) | 4 | ✅ Complete | Week 4 |
| **ollama-optimizer** | Explorer+Executor (A) | 2 | ✅ Complete | Week 4 |
| **skill-creator (refactor)** | Refactoring | 3 new | ✅ Complete | Week 5 |

---

## Architecture Blueprints

### 1. dont-make-me-think (Review Loop)
**Files to create**: 3 agents
- `agents/ui-analyst.md` — Run Krug checklist, return structured findings
- `agents/report-writer.md` — Format findings into scannable markdown
- `agents/fixer.md` — Suggest redesign recommendations

**Pattern**: Creator → Reviewer (fresh context) → revise if needed
**Data contract**: UI findings JSON, then recommendation markdown
**Implementation**: ~2-3 days
**Key detail**: Analyzer never modifies files; reviewer validates completeness

---

### 2. readme-to-landing-page (Review Loop)
**Files to create**: 3 agents
- `agents/researcher.md` — Extract story from project/README
- `agents/writer.md` — Generate landing-page-structured markdown
- `agents/reviewer.md` — Validate anti-slop rules (banned phrases, pruned prose)

**Pattern**: Research → Write → Review (validate anti-slop)
**Data contract**: Story elements → landing page draft → validation JSON
**Implementation**: ~2-3 days
**Key detail**: Reviewer validates against explicit anti-slop checklist, not subjective taste

---

### 3. cli-builder (Explorer+Executor with Approval Gates)
**Files to create**: 3 agents
- `agents/analyzer.md` — Read project, detect language, map module API
- `agents/designer.md` — Produce CLI design (command tree, options, library selection)
- `agents/executor.md` — Implement code, tests, commit per phase

**Pattern**: Analyze → [USER APPROVAL] → Design → [USER APPROVAL] → Plan (inline) → [USER APPROVAL] → Implement
**Data contract**: Analysis JSON → Design JSON → Implementation report
**Implementation**: ~3-4 days
**Key detail**: Approval gates stay in main agent; no subagent can delay user interaction

---

### 4. theme-transformer (Explorer+Executor with Accessibility Check)
**Files to create**: 3 agents
- `agents/style-auditor.md` — Audit current UI, produce color/font inventory
- `agents/theme-executor.md` — Transform CSS per theme tokens
- `agents/accessibility-checker.md` — Validate WCAG contrast, readability

**Pattern**: Audit → [USER APPROVAL] → Transform → Review Loop (validator → fixer → fresh validator, max 3 cycles)
**Data contract**: Style inventory JSON → accessibility report → remediation steps
**Implementation**: ~3-4 days
**Key detail**: Accessibility is fresh-context validation, not self-review by executor

---

### 5. code-optimizer (Sequential Fixer Loop)
**Files to create**: 6 agents
- `agents/code-analyzer.md` — Run 5 priority checks, emit issue manifest
- `agents/performance-fixer.md` → `agents/memory-fixer.md` → `agents/algorithm-fixer.md` → `agents/caching-fixer.md` → `agents/concurrency-fixer.md` — Each fixes one category with test verification

**Pattern**: Analyzer (parallel internal checks) → Sequential fixer loop (priority order)
**Data contract**: Issue manifest JSON → per-fixer result JSON
**Implementation**: ~4-5 days
**Key detail**: Fixers run sequentially (shared working tree), not parallel. Each fixer reverts on test failure.

---

### 6. test-coverage (Pipeline with Parallel Workers)
**Files to create**: 3 agents
- `agents/coverage-analyzer.md` — Run coverage tool, parse, module batching
- `agents/test-writer.md` — Write tests for one module (spawned in parallel, max 8)
- `agents/merge-assembler.md` — Resolve conflicts, produce final test files

**Pattern**: Analyze → [USER APPROVAL] → Parallel test writers → Assemble → [USER APPROVAL] → Apply + re-run coverage
**Data contract**: Coverage report JSON → per-writer test files → conflict report JSON
**Implementation**: ~3-4 days
**Key detail**: Parallel writers use namespace contracts to prevent test collisions; assembler owns deduplication

---

### 7. prd-generator (Staged Pipeline with Review)
**Files to create**: 3 agents
- `agents/requirements-extractor.md` — Read idea.md + validate.md, normalize to contract JSON
- `agents/prd-writer.md` — Generate full PRD per template, trace requirements
- `agents/prd-reviewer.md` — Validate completeness, traceability, placeholder check

**Pattern**: Extract → [USER CONFIRMATION if missing validate.md] → Write → Review ([HALT if NEEDS_FIX])
**Data contract**: Requirements JSON → PRD markdown → traceability validation JSON
**Implementation**: ~3-4 days
**Key detail**: Reviewer is fresh-context validation; traces every requirement ID into PRD

---

### 8. install-script-generator (Four-Phase Pipeline)
**Files to create**: 4 agents
- `agents/env-analyzer.md` — Detect OS, arch, package managers
- `agents/script-planner.md` — Design installation strategy
- `agents/script-generator.md` — Write install.sh + install.ps1
- `agents/script-validator.md` — Test script logic

**Pattern**: Detect → Plan → Generate → Validate (strictly sequential)
**Data contract**: Environment profile → plan JSON → script files → validation report
**Implementation**: ~2-3 days
**Key detail**: Stages are strictly sequential; no parallelism. Validator checks one-liner usability.

---

### 9. ollama-optimizer (Explorer+Executor)
**Files to create**: 2 agents
- `agents/system-analyzer.md` — Run detection script, classify tier, embed config rules
- `agents/guide-generator.md` — Generate optimization guide from profile JSON

**Pattern**: Detect (run scripts) → Generate (no scripts, pure prose)
**Data contract**: System profile JSON (with all tier rules pre-computed)
**Implementation**: ~2 days
**Key detail**: Analyzer embeds ALL reference file content into profile; generator never re-reads references

---

### 10. skill-creator (Refactoring)
**Files to create**: 3 agents (extract from monolithic SKILL.md)
- `agents/test-designer.md` — Design test cases or add assertions
- `agents/executor.md` — Run full eval round (spawn, grade, aggregate, viewer, analyst)
- `agents/description-optimizer.md` — Generate trigger evals, run optimization loop

**Pattern**: Refactoring existing orchestrator (no new functionality)
**Key change**: SKILL.md shrinks from 596 to ~270 lines
**Implementation**: ~2-3 days
**Risk**: Zero tolerance for regression — all existing behavior must survive verbatim

---

## Implementation Roadmap

### Phase 1: Quick Wins — Review Loop Skills (Week 1)
**Parallel**: dont-make-me-think + readme-to-landing-page

- [ ] Create agents/ directories for both skills
- [ ] Write both ui-analyst and researcher agents (data extraction)
- [ ] Write both report-writer and writer agents (markdown generation)
- [ ] Write both fixer and reviewer agents (validation)
- [ ] Update both SKILL.md files with Architecture + graceful degradation
- [ ] Update both README.md files with mermaid diagrams

**Acceptance**: Both skills tested end-to-end with sample inputs

---

### Phase 2: Explorer+Executor Cohort (Week 2)
**Parallel**: cli-builder + theme-transformer + code-optimizer (start)

- [ ] Create agents/ for cli-builder, theme-transformer
- [ ] Write analyzer/designer/executor for cli-builder
- [ ] Write auditor/executor/checker for theme-transformer
- [ ] Preserve all approval gates (inline in main agent)
- [ ] Start code-optimizer: create all 6 agent files
- [ ] Update all three SKILL.md files

**Acceptance**: cli-builder and theme-transformer tested; code-optimizer agents drafted

---

### Phase 3: Complex Patterns — Pipeline & Parallel (Weeks 3-4)
**Sequential**: install-script-generator → test-coverage → ollama-optimizer

- [ ] Implement install-script-generator (4-phase pipeline)
- [ ] Test with sample software, verify one-liner usage
- [ ] Implement test-coverage (3-stage with parallel workers)
- [ ] Test coverage batching algorithm; verify merge deduplication
- [ ] Implement ollama-optimizer (2 agents)
- [ ] Test on Mac (unified memory), Linux (NVIDIA), CPU-only

**Acceptance**: All three skills function independently

---

### Phase 4: Dependent Skills & Refactoring (Week 5)
**Sequential**: prd-generator (depends on integration) → skill-creator (refactoring)

- [ ] Implement prd-generator (3-stage pipeline)
- [ ] Test with sample idea.md + validate.md
- [ ] Test graceful degradation when validate.md missing
- [ ] Refactor skill-creator: extract 3 agents, reduce SKILL.md to <300 lines
- [ ] Regression test: run skill-creator on a sample skill end-to-end
- [ ] Verify all timing capture, grading, viewer, description optimization paths work

**Acceptance**: prd-generator produces correct traceability; skill-creator regression tests pass

---

## Common Patterns & Conventions

### Data Contract Pattern (used across all skills)
```json
{
  "phase": 1,
  "status": "success | error",
  "data": { /* phase-specific structure */ },
  "error_details": { /* only if status=error */ }
}
```

Every inter-agent data exchange uses a workspace directory with JSON files at known paths.

### Graceful Degradation Template (required for every skill)
```markdown
## Environment Check

This skill uses subagents for [X], [Y], [Z].

If the Agent tool is not available (Claude.ai), execute each phase inline instead:
- Phase 1: [action inline]
- Phase 2: [action inline]
- Phase 3: [action inline]
```

### Approval Gate Pattern (for skills with user decisions)
```markdown
[Subagent produces artifact]
[Main agent presents to user for approval]
[HALT here — subagent must not proceed without explicit user confirmation]
[User approves]
[Continue to next phase]
```

Subagents must NEVER ask users for input directly.

### Fresh-Context Validation (for Review Loop skills)
The reviewer subagent is spawned AFTER creation is complete. It reads the output file with no context about how it was created. This prevents the reviewer from rationalizing away issues the creator already committed to.

---

## File Organization

```
skills/
├── dont-make-me-think/
│   ├── SKILL.md (v1.2.0 → 2.0.0)
│   ├── README.md (update diagram)
│   └── agents/
│       ├── ui-analyst.md (new)
│       ├── report-writer.md (new)
│       └── fixer.md (new)
│
├── cli-builder/
│   ├── SKILL.md (v1.0.0 → 2.0.0)
│   ├── README.md (update diagram)
│   └── agents/
│       ├── analyzer.md (new)
│       ├── designer.md (new)
│       └── executor.md (new)
│
... (same pattern for other 8 skills)
│
└── skill-creator/
    ├── SKILL.md (v1.2.0 → 1.3.0, refactor from 596 to ~270 lines)
    ├── README.md (no change)
    └── agents/
        ├── test-designer.md (new)
        ├── executor.md (new)
        ├── description-optimizer.md (new)
        ├── grader.md (existing, unchanged)
        ├── comparator.md (existing, unchanged)
        └── analyzer.md (existing, unchanged)
```

---

## Success Criteria

For EACH MEDIUM-priority skill implementation:

1. ✅ **Subagents are isolated** — each agent prompt file has complete, focused instructions
2. ✅ **Main agent is orchestrator** — SKILL.md delegates heavy work, retains decision-making
3. ✅ **Data contracts are enforced** — JSON structures match between agents
4. ✅ **Graceful degradation works** — skill functions without Agent tool (inline fallback)
5. ✅ **SKILL.md < 500 lines** — if exceeds, move content to agent files
6. ✅ **README.md updated** — includes `agents/` resources table
7. ✅ **Regression tests pass** — skill produces identical output to prior version
8. ✅ **Error handling is explicit** — all failure modes have documented recovery paths

---

## Estimated Token Budget

**Per-skill average**:
- 3-agent skill: ~40-50KB of complete prompts + SKILL.md + README updates
- 4+ agent skill: ~60-80KB
- Refactoring (skill-creator): ~75KB of combined files

**Total across 10 skills**: ~600KB of new agent files + 10 updated SKILL.md files

---

## Next Steps

### Immediate (User approval)
1. User reviews this document and all sub-documents
2. User approves implementation start

### Week 1 Execution
1. Launch Phase 1 (Review Loop): dont-make-me-think + readme-to-landing-page
2. Implement agents/, update SKILL.md, update README.md
3. Test both skills end-to-end
4. Move to Phase 2 (Explorer+Executor cohort)

### Ongoing
- Track progress in DEPLOYMENT_CHECKLIST.md
- Document any deviations from architecture in per-skill IMPLEMENTATION_NOTES.md
- Keep regression test results in each skill's workspace

---

## Critical Success Factors

1. **Preserve all approval gates** — subagents must NEVER bypass user confirmation points
2. **No re-reading files** — each subagent reads its specific inputs once; main agent reads subagent outputs
3. **Fresh-context validators** — review agents are spawned after creation, not inline
4. **Workspace file contracts** — every agent writes to known paths; orchestrator reads only the paths, not raw output
5. **Graceful degradation** — every skill works both with and without Agent tool
6. **Test regression thoroughly** — skill-creator refactoring is zero-tolerance; others should maintain output equivalence

---

## Document Cross-References

- **dont-make-me-think**: Full architecture at [linked output file]
- **readme-to-landing-page**: Full architecture at [linked output file]
- **cli-builder**: Full architecture with complete agent prompts at [linked output file]
- **theme-transformer**: Full architecture at [linked output file]
- **code-optimizer**: Full architecture with 6 agent specs at [linked output file]
- **test-coverage**: Full architecture with parallel worker pattern at [linked output file]
- **prd-generator**: Full architecture with staged pipeline at [linked output file]
- **install-script-generator**: Full architecture at [linked output file]
- **ollama-optimizer**: Full architecture at [linked output file]
- **skill-creator**: Refactoring plan with 3 extracted agents at [linked output file]

---

**Status**: ✅ Ready for implementation
**Complexity**: HIGH (10 skills in parallel)
**Duration**: 4-5 weeks full-time equivalent
**Risk**: MEDIUM (subagent patterns proven in HIGH-priority pilot; apply to MEDIUM cohort with confidence)

---

## Approval & Sign-Off

- [ ] User reviews architecture documents (this + 10 linked files)
- [ ] User approves implementation start
- [ ] User confirms Phase 1 timeline (Week 1)
- [ ] (Optional) User designates alternate implementation owner/reviewer

Once approved, implementation begins immediately with Phase 1 (Review Loop skills).
