# NVIDIA NeMo Components: Status, Replacements & NVAIE Coverage

_Snapshot: 2026-11-03. Sources: NeMo docs hub, NeMo Microservices archive banner, NAT migration guide, NeMo Helix docs, NGC "NVIDIA AI Enterprise Supported" label filter._

| NeMo component | What it is / used for | Status | Replacement | In NVAIE? | Closest NVAIE alternative |
|---|---|---|---|---|---|
| **NeMo Framework** (collection) | Umbrella name for the open-source training-side libraries in the rows below. Not installable as one thing | ✅ Live | — | ⚠️ Only through the Megatron Backend container | — |
| **NeMo Framework Megatron Backend** (container) | Ready-to-run image for pretraining, SFT, LoRA and RLHF at multi-node scale. Bundles Megatron-Core and Megatron-Bridge, plus Export-Deploy | ✅ Live | — | ✅ Yes | — |
| **Megatron-Bridge** | Converts Hugging Face ↔ Megatron checkpoints; trains and fine-tunes large models using Megatron-Core parallelism | ✅ Live | — | ✅ Inside the FW container² | — |
| **Export and Deploy** | Exports trained models to TensorRT, TensorRT-LLM or vLLM and serves them via Triton or Ray | ✅ Live | — | ✅ Inside the FW container² | Also: TensorRT, Triton, Dynamo Enterprise |
| **NeMo Run** | Launches and tracks training and eval jobs on local, Slurm, Kubernetes or cloud clusters | ✅ Live | — | ⚠️ Probably inside the FW container, not confirmed | NeMo FW container |
| **NeMo Retriever** | RAG building blocks: document extraction (OCR, tables, charts), embedding and reranking NIMs | ✅ Live | — | ✅ Yes | — |
| **NeMo Curator** | GPU-accelerated data cleaning: dedup, quality filtering and classification for training data | ✅ Live | — | ❌ No | RAPIDS (you write the pipeline yourself) |
| **NeMo RL** | Post-training and alignment library: GRPO, DPO, SFT, distillation | ✅ Live | — | ❌ No | NeMo FW container (SFT, LoRA, RLHF) |
| **NeMo AutoModel** | Fine-tunes Hugging Face models the day they're released, with native PyTorch parallelism | ✅ Live | — | ❌ No | NeMo FW container or PyTorch container |
| **NeMo Evaluator** (library) | Runs benchmarks and LLM-as-judge evals against models and endpoints | ✅ Live | — | ❌ No | ⛔ None |
| **NeMo Guardrails** (library) | Programmable rails for LLM apps: topic control, jailbreak, PII, fact-checking | ✅ Live | — | ❌ No | Partial: Nemotron 3.5 Content Safety NIM (a model, not a rails engine) |
| **NeMo Gym** | Simulated environments that generate rollout data for agentic RL training and evaluation | ✅ Live | — | ❌ No | ⛔ None |
| **NeMo Skills** | Reference pipelines for synthetic data, training and benchmark evaluation (e.g. math and code reasoning) | ✅ Live | — | ❌ No | NeMo FW container |
| **NeMo Speech** | Trains speech models (ASR, TTS) and exports them to Riva | ✅ Live | — | ❌ No (standalone) | Riva (to deploy) + NeMo FW container (to train) |
| **NeMo VFM** | Trains vision foundation models | ⚠️ Doc link returns 404 | — | ❌ No | TAO Toolkit |
| **NeMo Microservices** (umbrella) | Containerized REST APIs on Kubernetes that wrap customization, eval, guardrails and data generation | ❌ Sunset Oct 1, 2026 | NeMo Platform, now **NeMo Helix** | ❌ No¹ | — |
| **NeMo Customizer** (microservice) | API-driven fine-tuning jobs (LoRA, SFT, DPO) on your data | ❌ Archived | Helix → *Fine-tune Models* | ❌ No¹ | NeMo FW container |
| **NeMo Evaluator** (microservice) | API-driven eval jobs: benchmarks, LLM-as-judge, RAG and agent metrics | ❌ Archived | Helix → *Evaluate Agents & Models* | ❌ No¹ | ⛔ None |
| **NeMo Guardrails** (microservice) | Guardrails hosted as a service in front of model endpoints | ❌ Archived | Helix → *Guardrail Models* | ❌ No¹ | Content Safety NIM (partial) |
| **NeMo Data Designer** (microservice) | Synthetic dataset generation with previews and validation | ❌ Archived | Helix → *Design Synthetic Data* | ❌ No¹ | Build it yourself on LLM NIMs |
| **NeMo Auditor** (microservice) | Red-teaming and vulnerability scanning of models with garak | ❌ Archived | Helix → *Vulnerability Scanning* | ❌ No¹ | ⛔ None |
| **NeMo Safe Synthesizer** (microservice) | Privacy-safe synthetic copies of sensitive data (PII replacement, differential privacy) | ❌ Archived | Helix → *Synthesize Safe Data* | ❌ No¹ | ⛔ None |
| **NeMo Agent Toolkit** | Framework-agnostic agent profiling, eval, optimization and observability (wraps LangGraph, ADK etc.) | ❌ Deprecated, end of life end of 2026 | NeMo Relay, NeMo Fabric and NeMo Helix (see mapping below) | ❌ No | ⛔ None |
| **NeMo Helix** | Self-hosted control plane to evaluate, tune, harden, run and fine-tune agents (CLI, API, SDK, Studio UI) | ✅ New | — | ❌ No | For serving only: NIM + NIM Operator + Dynamo Enterprise |
| **NeMo Relay** | Agent runtime layer: traces LLM and tool calls, middleware, policy and governance, without changing your agent code | ✅ New | — | ❌ No | ⛔ None. Use OpenTelemetry |
| **NeMo Fabric** | One interface to configure and run agent harnesses and custom agents (models, tools, MCP), with normalized results | ✅ New | — | ❌ No | ⛔ None |

**Notes**

1. On NGC, the microservices are listed under their own **"NeMo Microservices"** product, not under the NVAIE label.
2. Inferred from the Megatron Backend container's 26.10 release notes, which mention Megatron-Bridge and Export-Deploy.
3. The NVAIE column reflects the NGC label as of 2026-11-03. Before relying on support coverage, confirm it with your NVIDIA account team.

## NeMo Agent Toolkit → successor mapping

NVIDIA's migration guide names only the three successor projects. The feature-level mapping below is my own reading of their docs.

| What you used in NAT | Replacement |
|---|---|
| Profiling, telemetry exporters, middleware (HITL, circuit breaker) | **NeMo Relay**: scopes, middleware, plugins, exporters |
| Running workflows and agents, wiring up tools and MCP servers | **NeMo Fabric**: harness adapters |
| `nat eval` | NeMo Helix → *Evaluate Agents & Models* |
| `nat optimize` (prompt and hyperparameter tuning) | NeMo Helix → *Optimize Agents* (prompt and hyperparameter tuning, skill optimization, Switchyard routing) |
| Red-teaming and safety | NeMo Helix → *Vulnerability Scanning* (garak) + *Agent Governance* (war-games) |
| Serving and deploying agents | NeMo Helix → *Deploy Agents* / *Execute Agents as Jobs* (still supports existing NAT-based LangGraph agents as "legacy") |

## Sources

- [NeMo docs hub](https://docs.nvidia.com/nemo/index.html)
- [NeMo Microservices (archived)](https://archive.docs.nvidia.com/nemo/microservices/latest/)
- [NAT migration guide](https://docs.nvidia.com/nemo/agent-toolkit/latest/resources/migration-guide.html)
- [NeMo Helix docs](https://docs.nvidia.com/nemo-helix)
- [NeMo Relay ecosystem](https://docs.nvidia.com/nemo/relay/latest/about-nemo-relay/ecosystem)
- [NeMo Fabric ecosystem](https://docs.nvidia.com/nemo/fabric/latest/about-ne-mo-fabric/ecosystem)
- [NGC: NVIDIA AI Enterprise Supported, "nemo" search](https://catalog.ngc.nvidia.com/search?productNames=nvaie_supported&query=nemo)
- [NeMo Framework Megatron Backend container](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/nemo)
- [NVAIE Application Layer software](https://docs.nvidia.com/ai-enterprise/software/latest/application-software.html)
