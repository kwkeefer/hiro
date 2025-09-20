# ADR-017: Mission Tools Separation of Concerns

**Status**: Accepted
**Date**: 2025-01-21
**Author**: Development Team

## Context

While implementing Phase 4 (Intelligent Assistance) of the mission-based security testing architecture, we discovered significant overlap and confusion in our tool design:

1. Unclear distinction between "patterns" and "techniques"
2. Tools attempting to provide "guidance" that should be LLM reasoning
3. Overlapping analytics and intelligence tools
4. Too many tools making it hard for agents to choose

Key realizations:
- Tools were trying to be "smart" instead of just providing data
- "Patterns" added no value over "techniques"
- Auto-extraction of learnings requires judgment that belongs to the LLM
- Many analysis tools were just search with extra steps

## Decision

We will restructure mission tools following these principles:

### 1. Clear Separation: Tools Provide Data, LLMs Provide Reasoning

**Tools DO:**
- Store and retrieve facts
- Calculate statistics
- Perform vector similarity search
- Filter and sort data

**Tools DON'T:**
- Make recommendations
- Interpret results
- Decide what's important
- Generate strategies

### 2. Simplified Terminology

**Technique**: A method or approach (text description)
**Action**: A record of trying a technique
**Library**: Human/LLM-curated saved techniques

We DROP the term "pattern" entirely - it adds confusion without value.

### 3. Three Clear Categories

```python
# Core Operations (During Testing)
- create_mission()
- set_mission_context()
- get_mission_context()  # Includes basic stats
- record_action(technique, success, learning)

# Search (Finding What Worked)
- find_similar_techniques()  # Vector similarity
- search_techniques()  # With filters for success/type/rate
- get_technique_stats()  # Usage count, success rate

# Knowledge Library (Curated Learnings)
- add_to_library()  # LLM decides what's worth saving
- search_library()  # Find curated knowledge
```

### 4. No Auto-Extraction

We reject "auto-extract successful techniques" because:
- Arbitrary thresholds (>80% success? 3+ uses?)
- Can't generate meaningful descriptions
- The LLM knows WHY something matters, we don't

## Implementation Details

```python
# Good: Pure data retrieval
async def get_technique_stats(technique: str) -> dict:
    return {
        "success_rate": 0.75,
        "usage_count": 23,
        "failed_contexts": ["WAF present", "auth required"],
    }

# Bad: Trying to interpret
async def suggest_next_action() -> str:
    return "You should try SQL injection"  # LLM's job

# Good: Factual search
async def search_techniques(
    success_only: bool = True,
    mission_type: str = None,
    min_success_rate: float = None
) -> list[dict]:
    # Returns raw data, LLM interprets

# Bad: Making decisions
async def auto_extract_patterns() -> None:
    # Saves "important" techniques  # How do we know what's important?
```

## Consequences

### Positive
- **Clear mental model**: Each tool has one obvious purpose
- **Reduced complexity**: ~10 tools instead of 20+
- **Better AI agents**: LLMs can reason better with clean data
- **Maintainable**: Simple tools are easier to test and debug
- **Flexible**: LLMs can interpret data differently per context

### Negative
- **More LLM work**: Agents must interpret raw data
- **No magic**: Tools won't automatically build knowledge
- **Manual curation**: Valuable techniques must be explicitly saved

## Alternatives Considered

### 1. Smart Guidance Tools
Create tools that analyze context and suggest next steps.
- **Rejected**: This is the LLM's core competency, not ours

### 2. Auto-Pattern Extraction
Automatically identify and save successful patterns.
- **Rejected**: Requires judgment about what's valuable

### 3. Complex Analytics Suite
Multiple specialized analysis tools for different insights.
- **Rejected**: Most analytics are just filtered searches

### 4. Keep "Patterns" Terminology
Maintain distinction between techniques and patterns.
- **Rejected**: Adds complexity without clear value

## Example Workflow

```python
# 1. During testing (Core)
await set_mission_context(mission_id="...")
await record_action(
    technique="SQL injection in user parameter",
    success=True,
    learning="Worked with unicode encoding"
)

# 2. Agent wants to know what else might work (Search)
similar = await find_similar_techniques("SQL injection")
stats = await get_technique_stats("SQL injection")
# LLM: "Based on 75% success rate and similar technique X..."

# 3. Agent decides this is valuable (Library)
await add_to_library(
    title="Unicode SQL Injection",
    content="Bypasses WAF using unicode encoding...",
    category="exploit"
)

# 4. Later missions (Search Library)
knowledge = await search_library("WAF bypass")
# Returns curated techniques with full context
```

## Related ADRs

- **ADR-016**: Mission Context Management - This simplification aligns with provider-level context
- **ADR-009**: Composition Over Inheritance - Tools compose, don't inherit intelligence
- **ADR-012**: Self-Descriptive Code - Simple tools with clear names

## Migration Path

1. Consolidate existing tools into three categories
2. Remove "pattern" terminology from codebase
3. Eliminate guidance/suggestion functions
4. Simplify analytics to basic search operations
5. Update tool descriptions to be data-focused

## Summary

Tools are for data operations. LLMs are for reasoning. This separation creates a cleaner, more maintainable, and more powerful system where each component does what it does best.
