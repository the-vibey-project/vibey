# Prior-art search log (PRISMA-lite)

Track: PRIOR-ART. Question: does a method already exist that gives a verdict on >=95% of
large diffs in bounded time on a local gpt-oss:20b (Ollama, one slot, ~22 tok/s generation,
~250-300 tok/s prompt eval, 65,536-token window, no paid API) without losing recall or adding
false positives, and what does the evidence say?

- Date of every search: 2026-10-01 (all queries run in one session; cutoff = that date).
- Searcher: Claude (prior-art agent). No local Ollama model was invoked; the only local
  command touching Ollama was `ollama --version` (reports server 0.35.0, client 0.32.15).
- Hit counts are what the tool returned for that call (tools cap results; counts are not
  corpus totals).
- Inclusion criteria: (I1) describes a mechanism for large-diff / long-input code review, or
  (I2) controls/forces reasoning length in reasoning models, or (I3) gives quantitative
  evidence on review recall/precision/verdict reliability, or (I4) gives exact runtime
  facts for Ollama / harmony / gpt-oss. Exclusion: (E1) off-topic, (E2) marketing with no
  mechanism or number, (E3) duplicate, (E4) inaccessible, (E5) training-only methods we
  cannot apply (kept only as context).
- Decision codes: INC = included and read (full text, source code or primary doc),
  INC-A = included from abstract/snippet only, EXC-n = excluded with reason.

## Flow summary

| Stage | Count |
|---|---|
| Records identified (sum of tool returns, incl. code/doc fetches) | ~230 |
| Duplicates / repeats across tools | ~25 |
| Screened (title + snippet/abstract) | ~205 |
| Excluded at screening (E1/E2) | ~150 |
| Assessed in full (paper text via alphaXiv, primary docs, source code) | 41 |
| Included in synthesis (sources.md) | 52 (41 INC, 11 INC-A) |

## Log

| # | Tool | Query / target | Hits | Decisions |
|---|---|---|---|---|
| 1 | Context7 resolve-library-id | "Ollama" (gpt-oss think levels, raw, num_predict) | 5 libs | `/ollama/ollama` chosen (High reputation) |
| 2 | WebFetch | cookbook.openai.com/articles/openai-harmony | 1 (308 redirect) | followed to developers.openai.com; INC (harmony tokens, channels, "Reasoning: high") |
| 3 | Context7 query-docs | /ollama/ollama: think low/medium/high for gpt-oss | 4 snippets | INC (gpt-oss accepts only low/medium/high; bool ignored) |
| 4 | Firecrawl developer_search | "ollama gpt-oss raw mode generate harmony template prefill assistant final channel" | 9 | INC: OpenAI raw-CoT cookbook, HF blog (channel structure), Ollama PR #18479, rapid-mlx #1067 (channel-skip raw prompt works on gpt-oss-20b), harmony format.md, arXiv 2604.00362 (INC-A); EXC-1: fine-tune blogs |
| 5 | Context7 query-docs | /ollama/ollama: raw param, num_predict, num_ctx, done_reason | 4 snippets | INC (raw bypasses template; DoneReasonLength = num_predict or ctx limit) |
| 6 | Firecrawl developer_search | "ollama gpt-oss raw: true generate thinking parser harmony output not parsed" | 9 | INC: docs.ollama.com thinking page (`/api/show` thinking values, default medium); towardsai article EXC-4 (HTTP 403) |
| 7 | Firecrawl developer_search | "ollama thinking budget max thinking tokens gpt-oss issue limit reasoning length" | 9 | INC: ollama issue #17561 (open proposal), goose #11142 (shared max_tokens -> empty answer), Together gpt-oss tips; EXC-2: gateway docs |
| 8 | WebFetch | github.com/ollama/ollama/issues/17561 | 1 | INC (open, no maintainer reply; Gemma-4 measurements; relies on llama.cpp reasoning-budget) |
| 9 | Firecrawl developer_search | "llama.cpp reasoning-budget sampler gpt-oss harmony forced end of thinking reasoning_budget_message" | 8 | INC: llama.cpp PR #20297, llama-cpp-python README, tabbyAPI doc (INC-A); EXC-3 HN comment |
| 10 | WebFetch | github.com/ggml-org/llama.cpp/pull/20297 | 1 | INC (merged 2026-03-11; budget message 89% vs 79% without; harmony support not stated) |
| 11 | WebFetch | pub.towardsai.net Ollama 0.34.4 article | 0 | EXC-4 (403) |
| 12 | Bash curl (raw.githubusercontent / api.github.com) | ollama/ollama main: server/routes.go, llm/llama_server.go, llm/server.go, server/prompt.go, harmony/harmonyparser.go; repo tree; commits; releases; ollama.com gpt-oss:20b template + params blobs | 9 files | INC (primary source code; see findings sec. 3). harmonyparser.go last commit a9d8953ab0, 2026-09-22; latest release v0.35.1-rc0 2026-09-29 |
| 13 | alphaXiv get_paper_content + answer_pdf_queries | arXiv 2508.10925 (gpt-oss model card) | 1 | INC (effort levels, Table 3 per-effort scores, ">20k CoT tokens per AIME problem" for 20b) |
| 14 | WebFetch | qodo-merge-docs.qodo.ai compression_strategy, large_prs | 2 (301 to docs.qodo.ai) | not followed; replaced by #15 (primary source) |
| 15 | Bash curl | qodo-ai/pr-agent main: pr_processing.py, configuration.toml, compression_strategy.md, dynamic_context.md, pr_code_suggestions.py, reflect prompt | 6 files | INC (repo last commit 2b73b361cf, 2026-10-01) |
| 16 | Exa web_search | "CodeRabbit how it reviews large pull requests file limit, chunking, incremental review" | 8 | INC: plans (file limits), auto-review (incremental), Change Stack; EXC-2: rate-limit pricing pages (kept only for limits) |
| 17 | WebFetch | github.com/coderabbitai/ai-pr-reviewer | 0 | EXC-4 (404 at fetch time); recovered via #47 |
| 18 | Exa web_search | "engineering blog how an AI code review bot handles very large pull requests (Greptile, Graphite Diamond, Ellipsis, Bito, Sourcery)" | 10 | INC-A: Greptile nit-filtering case study (19% -> 55% addressed, vendor), Greptile multi-model routing, Copilot huge-PR rendering (EXC-1, UI only), Graphite context guide; EXC-2: comparison listicles |
| 19 | alphaXiv discover_papers | code review benchmarks, false positives, industrial (difficulty 7) | 15 | INC: 2603.23448 c-CRAB, 2509.01494 SWR-Bench, 2601.01129 RovoDev, 2603.26130 SWE-PRBench, 2608.02693 PRWeaver (INC-A); INC-A: 2601.19494 AACR-Bench, 2607.03316; EXC-1: 2609.04535 CodeQL FPs, 2606.19616 |
| 20 | alphaXiv discover_papers | budget forcing / overthinking / thinking budget / early exit (difficulty 7) | 12 | INC: 2604.06613 detection-extraction gap; INC-A: 2604.10739, 2605.17672, 2609.03633; EXC-1: 2607.08173 (auditing) |
| 21 | alphaXiv answer_pdf_queries | 2601.01129 RovoDev | 1 | INC |
| 22 | alphaXiv answer_pdf_queries | 2509.01494 SWR-Bench | 1 | INC |
| 23 | alphaXiv answer_pdf_queries | 2603.23448 c-CRAB | 1 | INC |
| 24 | alphaXiv answer_pdf_queries | 2501.19393 s1 budget forcing | 1 | INC |
| 25 | alphaXiv answer_pdf_queries | 2604.06613 detection-extraction gap | 1 | INC |
| 26 | alphaXiv discover_papers | interrupting reasoning models / forced answer / gpt-oss | 11 | INC: 2510.11713 (tests GPT-OSS-20B); INC-A: 2603.05488 reasoning theater, 2604.04930; EXC-1: 2605.28070 |
| 27 | alphaXiv answer_pdf_queries | 2510.11713 Are LRMs interruptible? | 1 | INC |
| 28 | alphaXiv discover_papers | long context degrades reasoning; lost in the middle; LongCodeBench/RULER (historical) | 13 | INC: 2510.05381, 2604.01161; INC-A: 2307.03172 lost in the middle, 2505.00127; EXC-5: 2606.23687 (training) ; not read: LongCodeBench, RULER (gap, see findings sec. 6) |
| 29 | alphaXiv answer_pdf_queries | 2604.01161 Reasoning Shift | 1 | INC (includes gpt-oss-120b) |
| 30 | alphaXiv answer_pdf_queries | 2510.05381 Context length alone hurts | 1 | INC |
| 31 | alphaXiv discover_papers | industrial LLM code review (AutoCommenter, Meta, Ericsson, Beko, ...) (historical) | 10 | INC: 2405.13565, 2605.30208, 2507.19115, 2412.18531, 2501.15134; INC-A: 2609.15877; EXC-1: 2601.01514, 2609.29172 |
| 32 | alphaXiv answer_pdf_queries | 2501.15134 BitsAI-CR | 1 | INC |
| 33 | alphaXiv answer_pdf_queries | 2605.30208 Meta RADAR | 1 | INC |
| 34 | alphaXiv answer_pdf_queries | 2507.19115 Ericsson | 1 | INC |
| 35 | alphaXiv answer_pdf_queries | 2412.18531 Beko / PR-Agent in practice | 1 | INC |
| 36 | alphaXiv discover_papers | mutation / injected bugs to evaluate LLM reviewers | 11 | INC: 2606.15689; INC-A: 2607.21656; EXC-1: test-generation mutation papers |
| 37 | Firecrawl research_search_papers | "evaluate LLM code review by injecting synthetic bugs ... detection rate and false alarm rate, diff size effect" (from 2023-01-01) | 12 | INC: 2606.15689, 2603.26130, 2607.09979; INC-A: 2608.02693, 2505.17928, 2604.19049, 2504.04372; EXC-1: 2606.29088, 2508.16419, 2508.04448 |
| 38 | alphaXiv answer_pdf_queries | 2606.15689, 2603.26130, 2607.09979 | 3 | INC (all three) |
| 39 | Exa web_search | "GitHub Copilot code review limitations large PRs; Gemini Code Assist limits" | 6 | INC: GitHub changelog 2025-07-02 and 2026-08-27 (300-file/20k-line limit lifted), Copilot docs (excluded file types, Lite/Balanced); INC-A: Gemini Code Assist doc |
| 40 | WebFetch | aider.chat/docs/repomap.html | 1 | INC (tree-sitter + graph ranking, `--map-tokens` default 1,000) |
| 41 | alphaXiv answer_pdf_queries | 2405.13565 AutoCommenter | 1 | INC |
| 42 | WebFetch | research.google/blog/resolving-code-review-comments-with-ml/ | 1 | INC (52% addressed at 50% target precision) |
| 43 | Firecrawl developer_search | "gpt-oss-20b endless reasoning loop repetition never produces final answer" | 9 | INC: 2509.23882 reasoning blackholes; INC-A: Artificial Analysis verbosity; EXC-2 vendor pages |
| 44 | alphaXiv answer_pdf_queries | 2509.23882 | 1 | INC (81% loops under greedy decoding) |
| 45 | Bash grep (local, read-only) | vibey `src/vibey_tools/gh/vibey_gh/config.py` sovereign review settings | 1 file | INC as context (temperature 0, reasoning_reserve 16,384, think empty, max_chunks 6) |
| 46 | HF hf_fs + Bash curl | hf://models/openai/gpt-oss-20b README + generation_config.json; github openai/gpt-oss README; ollama.com gpt-oss params | 4 | INC (recommended temperature 1.0, top_p 1.0; EOS ids; Ollama ships `temperature 1`) |
| 47 | Exa web_search | "Microsoft AI-powered code review at scale; Graphite Diamond false-positive rate; Sourcery" | 8 | INC: Microsoft devblog 2025-07-14, GitHub blog "60 million Copilot code reviews" 2026-03-05, Graphite launch (vendor <3% FP claim), Braintrust/Graphite case study (INC-A); EXC-2 Sourcery comparison page; EXC-1 Coral reviewer recommendation |
| 48 | Firecrawl research_search_papers | overthinking / inverse scaling / efficient reasoning survey (2024-12 to 2025-09) | 8 | INC-A: 2506.04210, 2504.15895, 2502.12215, 2507.14417, 2412.21187, 2503.16419; EXC-1: 2502.10954 (vision RNN) |
| 49 | Exa web_search | "coderabbitai ai-pr-reviewer README light model heavy model triage" | 5 | INC: ai-pr-reviewer README, CodeRabbit blog 2023-12-22 (triage saves ~50% cost, vendor) |
| 50 | Exa web_search | "Amazon Q Developer code review, Bito, Ellipsis, reviewdog LLM large PRs" | 8 | INC-A: Bito docs (auto-review up to 5,000 lines), Ellipsis engineering blog (hallucinations rise past half the context, vendor), Ellipsis docs (incremental review); EXC-2: Amazon Q blogs (no large-diff mechanism stated) |

## Coverage gaps (honest)

- Not found / not read in full: Sweep, reviewdog+LLM integrations (no mechanism doc found
  in one search), Mozilla's review-comment work, JetBrains, LLaMA-Reviewer and CodeReviewer
  papers in the original (their scores were taken second-hand from SWR-Bench Table 4),
  RULER and LongCodeBench (only cited, not read), Amazon CodeGuru (superseded; no
  large-diff mechanism doc found).
- Single-session search; no forward/backward citation chasing beyond what the papers cited.
- Several 2026 arXiv preprints are not peer reviewed; flagged per source in sources.md.
