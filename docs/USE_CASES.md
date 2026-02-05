# AOrchestra Use Cases

Real-world applications of agent orchestration.

## 1. Financial Analysis Pipeline

**Goal:** "Analyze Q3 earnings for NVDA, AMD, and INTC. Compare margins, growth, and provide investment recommendation."

**Orchestration:**
```
Decompose → 
  1. Fetch NVDA Q3 data (web_search)
  2. Fetch AMD Q3 data (web_search)  
  3. Fetch INTC Q3 data (web_search)
  4. Calculate margin comparisons (calculator)
  5. Analyze growth rates (calculator)
  6. Synthesize recommendation (LLM)
```

**Why orchestrate:** Each company lookup is independent (parallel), calculations depend on data, final synthesis depends on all.

---

## 2. Code Review & Refactor

**Goal:** "Review auth.py for security issues, suggest fixes, generate tests."

**Orchestration:**
```
Decompose →
  1. Read auth.py (file_read)
  2. Security audit - SQLi, XSS, auth bypass (code_analyze)
  3. Generate fixes for each issue (code_generate)
  4. Generate unit tests (code_generate)
  5. Run tests to verify (code_execute)
```

**Why orchestrate:** Security audit informs fixes, fixes inform tests, tests verify fixes. Sequential with feedback.

---

## 3. Customer Support Triage

**Goal:** "Handle incoming ticket: 'My order #12345 hasn't arrived'"

**Orchestration:**
```
Decompose →
  1. Extract order ID (LLM parse)
  2. Lookup order status (database_query)
  3. Check shipping carrier (api_call)
  4. Determine issue category (LLM classify)
  5. Generate response with tracking/refund info (LLM)
```

**Why orchestrate:** Each step builds context for next. Different tools needed. Cost-aware: use Flash for parsing, Premium for response.

---

## 4. Research Paper Summarization

**Goal:** "Summarize arxiv paper 2401.12345 and compare to related work"

**Orchestration:**
```
Decompose →
  1. Fetch paper PDF (web_fetch)
  2. Extract key findings (LLM summarize)
  3. Identify citations (LLM parse)
  4. Fetch 3 most relevant cited papers (web_fetch, parallel)
  5. Compare methodologies (LLM analyze)
  6. Generate comparative summary (LLM)
```

**Why orchestrate:** Long context handled in chunks. Related work fetched in parallel. Final comparison needs all summaries.

---

## 5. Multi-Step Data ETL

**Goal:** "Extract sales data from CRM, transform for analytics, load to warehouse"

**Orchestration:**
```
Decompose →
  1. Query CRM API for last 30 days (api_call)
  2. Validate data schema (code_execute)
  3. Clean nulls and normalize dates (code_execute)
  4. Calculate derived metrics (calculator)
  5. Format for warehouse schema (code_execute)
  6. Bulk insert to warehouse (database_write)
  7. Verify row counts match (database_query)
```

**Why orchestrate:** Pipeline with validation gates. Each step can fail and needs retry logic. Verification at end.

---

## 6. Content Creation Workflow

**Goal:** "Write a blog post about Rust async patterns"

**Orchestration:**
```
Decompose →
  1. Research current best practices (web_search)
  2. Generate outline with key points (LLM)
  3. Draft introduction (LLM, creative temp)
  4. Draft technical sections (LLM, precise temp)
  5. Generate code examples (code_generate)
  6. Verify code compiles (code_execute)
  7. Draft conclusion (LLM)
  8. SEO optimization pass (LLM)
```

**Why orchestrate:** Different temperature/model needs per section. Code must compile. Parallel drafting possible.

---

## 7. Automated Testing Suite

**Goal:** "Generate comprehensive tests for user_service.py"

**Orchestration:**
```
Decompose →
  1. Parse module structure (code_analyze)
  2. Identify public methods and signatures (code_analyze)
  3. Generate happy path tests (code_generate)
  4. Generate edge case tests (code_generate)
  5. Generate error handling tests (code_generate)
  6. Run all tests, collect failures (code_execute)
  7. Fix failing tests (code_generate)
  8. Verify 100% pass (code_execute)
```

**Why orchestrate:** Iterative refinement until all tests pass. Different test categories can be parallel.

---

## Cost-Aware Model Selection

AOrchestra's 3-tier routing optimizes cost:

| Task Type | Model Tier | Example |
|-----------|------------|---------|
| Data parsing | Flash | Extract order ID from text |
| Calculations | Flash | Sum totals, percentages |
| Classification | Standard | Categorize support tickets |
| Analysis | Standard | Compare financial metrics |
| Creative writing | Premium | Blog intro, marketing copy |
| Complex reasoning | Premium | Investment recommendations |

**Savings:** 60-80% cost reduction vs. using Premium for everything.

---

## Key Benefits

1. **Composability** - Build complex workflows from simple tools
2. **Observability** - Each step returns structured Observations  
3. **Cost control** - Right-size model for each sub-task
4. **Parallelism** - Independent tasks run concurrently
5. **Error handling** - Graceful degradation, retry logic
6. **Reusability** - Tools and sub-agents are modular
