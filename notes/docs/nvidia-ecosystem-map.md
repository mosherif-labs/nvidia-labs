# NVIDIA ecosystem map — tools and their AWS / Google / Microsoft / LangChain equivalents

*Last checked: 2026-10-29. ⭐ = heavy on NCP-AAI. "—" = no real equivalent.*

> **Status changes to remember**
> - **Triton → Dynamo-Triton** (renamed). **Dynamo** is NVIDIA's successor for distributed LLM serving.
> - **NeMo Microservices → NeMo Platform** (sunset Oct 1, 2026). Customizer, Evaluator, Guardrails, Auditor, Data Designer now live under NeMo Platform.
> - **NeMo Agent Toolkit (NAT) is deprecated** (Oct 2026, EOL end of 2026). Successors: **NeMo Relay** (observability, middleware, governance), **NeMo Helix** (CLI for eval, optimization, hardening), **NeMo Fabric** (one interface for agent harnesses and custom agents). NAT 1.0–1.8.0 has a CVSS 10.0 auth CVE (CVE-2026-65145, Oct 27, 2026).
> - **LangServe** deprecated (Nov 2024) → LangGraph Platform → renamed **LangSmith Deployment** (Oct 2025).
> - Exam note: the Nov 8 NCP-AAI blueprint predates the NAT deprecation, so still study NAT.

> **Type** — what kind of tool it is
> - ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) GPU acceleration: runs on, or makes things faster on, NVIDIA GPUs (CUDA libraries, compilers, inference runtimes, GPU data libraries).
> - ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) NeMo-family framework / API: you call it from code to build, customize, evaluate or guard models and agents.
> - ![Platform](https://img.shields.io/badge/Platform-F9A825?style=flat-square) hardware access, packaging, catalog, models or licensing.
> - Two type badges = an API or framework that ships GPU-optimized engines inside (e.g. TensorRT-LLM in NIM containers).

> **Domain** — each builds on the one before it
> - ![All](https://img.shields.io/badge/All-9E9E9E?style=flat-square) foundation; every AI workload runs on it.
> - ![ML](https://img.shields.io/badge/ML-00897B?style=flat-square) classic ML and general deep learning: tabular models (fraud scoring), vision, any trained network. Input → prediction.
> - ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) large generative models (LLMs, embeddings, diffusion) and RAG. Prompt → generated content.
> - ![Agentic](https://img.shields.io/badge/Agentic-EF6C00?style=flat-square) an LLM that plans, calls tools and loops toward a goal. Goal → actions.
> - Two domain badges = the tool serves both.

## 1. Compute and hardware access

| NVIDIA | Type | Domain | What it is | AWS | Google | Microsoft | LangChain |
|---|---|---|---|---|---|---|---|
| DGX / DGX Cloud (Lepton) | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![All](https://img.shields.io/badge/All-9E9E9E?style=flat-square) | NVIDIA GPU systems and GPU cloud | EC2 P5/P6, Trainium, Inferentia | A3/A4 VMs, TPU | ND H100/GB200 VMs, Maia | — |

## 2. GPU programming and core libraries

| NVIDIA | Type | Domain | What it is | AWS | Google | Microsoft | LangChain |
|---|---|---|---|---|---|---|---|
| CUDA | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![All](https://img.shields.io/badge/All-9E9E9E?style=flat-square) | Programming model and runtime for GPU code | Neuron SDK (Trainium/Inferentia) | XLA / JAX on TPU | — (uses CUDA; DirectML on Windows) | — |
| cuDNN / cuBLAS / CUTLASS | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![All](https://img.shields.io/badge/All-9E9E9E?style=flat-square) | Deep-learning primitives and matrix-math building blocks | Neuron kernels (NKI) | XLA ops, Pallas | — | — |
| NCCL | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![All](https://img.shields.io/badge/All-9E9E9E?style=flat-square) | Multi-GPU collective communication (all-reduce, etc.) | NCCL over EFA | TPU interconnect collectives | MSCCL / MSCCL++ | — |
| Transformer Engine | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | FP8/FP4 mixed-precision training | Neuron mixed precision | bf16 on TPU | — | — |
| Nsight Systems / Compute | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![All](https://img.shields.io/badge/All-9E9E9E?style=flat-square) | Profilers: system timeline / single kernel | Neuron Profiler | XProf / TPU profiler | — (PyTorch profiler) | — |
| DCGM | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![All](https://img.shields.io/badge/All-9E9E9E?style=flat-square) | GPU health and telemetry | CloudWatch | Cloud Monitoring | Azure Monitor | — |

## 3. Data

| NVIDIA | Type | Domain | What it is | AWS | Google | Microsoft | LangChain |
|---|---|---|---|---|---|---|---|
| RAPIDS (cuDF, cuML, cuGraph) | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![ML](https://img.shields.io/badge/ML-00897B?style=flat-square) | pandas, scikit-learn and graph analytics on GPU | EMR / Glue | BigQuery / Dataproc | Fabric / Synapse Spark | — |
| DALI | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![ML](https://img.shields.io/badge/ML-00897B?style=flat-square) | GPU data loading and augmentation | — | tf.data | — | — |
| NeMo Curator | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | Clean, dedupe and filter training data at scale | Glue, SageMaker Data Wrangler | Dataflow | Fabric pipelines | Document loaders, text splitters (lighter scope) |
| NeMo Data Designer / Safe Synthesizer | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | Synthetic data, and PII-safe synthetic data | Bedrock + SageMaker (DIY) | Vertex AI (DIY) | Foundry (DIY) | — |

## 4. Training and customization

| NVIDIA | Type | Domain | What it is | AWS | Google | Microsoft | LangChain |
|---|---|---|---|---|---|---|---|
| NeMo Framework (Megatron-Core, AutoModel, NeMo RL) | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | Pretraining, SFT, PEFT, RL alignment (DPO, GRPO) | SageMaker HyperPod | Vertex AI Training | Azure ML | — |
| ⭐ NeMo Customizer (NeMo Platform) | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | Fine-tuning as an API (LoRA, SFT, DPO) | Bedrock custom models | Vertex AI tuning | Foundry fine-tuning | — |
| Run:ai / Base Command Manager | ![Platform](https://img.shields.io/badge/Platform-F9A825?style=flat-square) | ![All](https://img.shields.io/badge/All-9E9E9E?style=flat-square) | GPU cluster scheduling and sharing | HyperPod task governance | GKE + Kueue | Azure ML compute | — |

## 5. Model optimization

| NVIDIA | Type | Domain | What it is | AWS | Google | Microsoft | LangChain |
|---|---|---|---|---|---|---|---|
| TensorRT | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![ML](https://img.shields.io/badge/ML-00897B?style=flat-square) | Compiles a model (usually ONNX) into an optimized inference engine | Neuron compiler | XLA | ONNX Runtime + Olive | — |
| ⭐ TensorRT-LLM | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | LLM inference engine: in-flight batching, paged KV cache, FP8/FP4 | SageMaker LMI containers | vLLM / JetStream on GKE | ONNX Runtime GenAI | — |
| Model Optimizer (ModelOpt) | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![ML](https://img.shields.io/badge/ML-00897B?style=flat-square) ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | Quantization, pruning, distillation, sparsity | SageMaker inference optimization | — | Olive | — |

## 6. Serving and deployment

| NVIDIA | Type | Domain | What it is | AWS | Google | Microsoft | LangChain |
|---|---|---|---|---|---|---|---|
| ⭐ NIM | ![Platform](https://img.shields.io/badge/Platform-F9A825?style=flat-square) ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | Prebuilt optimized model containers, OpenAI-compatible API | Bedrock (managed); SageMaker JumpStart | Vertex AI Model Garden | Foundry Models | — (ChatNVIDIA client only) |
| NIM Operator | ![Platform](https://img.shields.io/badge/Platform-F9A825?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | Kubernetes operator to deploy and cache NIMs | SageMaker on EKS | GKE Inference Gateway | AKS + KAITO | — |
| ⭐ Dynamo-Triton (ex-Triton) | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![ML](https://img.shields.io/badge/ML-00897B?style=flat-square) | Multi-framework model server: dynamic batching, ensembles | SageMaker endpoints | Vertex AI Prediction | Azure ML online endpoints | — |
| ⭐ Dynamo | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | Distributed LLM serving: disaggregated prefill/decode, KV-aware routing | — (vLLM / llm-d on EKS) | GKE + llm-d | — | — |
| AIPerf / GenAI-Perf | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | LLM load testing: TTFT, ITL, throughput | SageMaker Inference Recommender | GKE benchmarks | Foundry benchmarks | — |
| NGC Catalog | ![Platform](https://img.shields.io/badge/Platform-F9A825?style=flat-square) | ![All](https://img.shields.io/badge/All-9E9E9E?style=flat-square) | Registry of containers, models, Helm charts | ECR + JumpStart | Artifact Registry | Azure ML registry | LangChain Hub (prompts only) |
| *(agent hosting)* | — | ![Agentic](https://img.shields.io/badge/Agentic-EF6C00?style=flat-square) | Running agents as managed services | Bedrock AgentCore Runtime | Vertex AI Agent Engine | Foundry Agent Service | LangSmith Deployment (ex-LangGraph Platform; LangServe deprecated) |

## 7. Retrieval / RAG

| NVIDIA | Type | Domain | What it is | AWS | Google | Microsoft | LangChain |
|---|---|---|---|---|---|---|---|
| ⭐ NeMo Retriever | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | Embedding, reranking and document-extraction NIMs | Bedrock Knowledge Bases, Titan Embeddings, Rerank | Vertex AI RAG Engine, Search, Ranking API | Azure AI Search, Document Intelligence | Retrievers, Embeddings |
| cuVS | ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![ML](https://img.shields.io/badge/ML-00897B?style=flat-square) ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | GPU vector search (CAGRA), used inside Milvus etc. | OpenSearch | Vertex Vector Search (ScaNN) | Azure AI Search vectors | VectorStore abstraction |

## 8. Agents

| NVIDIA | Type | Domain | What it is | AWS | Google | Microsoft | LangChain |
|---|---|---|---|---|---|---|---|
| ⭐ NeMo Agent Toolkit (NAT) — **deprecated** | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) | ![Agentic](https://img.shields.io/badge/Agentic-EF6C00?style=flat-square) | Framework-agnostic agent config, profiling, eval, observability; MCP + A2A | Strands Agents, Bedrock AgentCore | ADK, Vertex AI Agent Engine | Agent Framework (Semantic Kernel + AutoGen), Foundry Agent Service | LangChain / LangGraph |
| NeMo Relay / Helix / Fabric (NAT successors) | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) | ![Agentic](https://img.shields.io/badge/Agentic-EF6C00?style=flat-square) | Relay: observability, middleware, governance · Helix: eval/optimize/harden CLI · Fabric: run agent harnesses | AgentCore Observability / Evaluations | Agent Engine, ADK eval | Foundry tracing / evaluations | LangSmith (tracing, evals) + LangSmith Deployment |
| AI Blueprints | ![Platform](https://img.shields.io/badge/Platform-F9A825?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) ![Agentic](https://img.shields.io/badge/Agentic-EF6C00?style=flat-square) | Reference apps (RAG, research agent, data flywheel) | AWS Solutions / samples | Agent Garden | Foundry templates | LangChain templates |
| Nemotron models | ![Platform](https://img.shields.io/badge/Platform-F9A825?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) ![Agentic](https://img.shields.io/badge/Agentic-EF6C00?style=flat-square) | NVIDIA open reasoning and agent models | Amazon Nova | Gemini / Gemma | Phi | — |

## 9. Evaluation, safety and guardrails

| NVIDIA | Type | Domain | What it is | AWS | Google | Microsoft | LangChain |
|---|---|---|---|---|---|---|---|
| ⭐ NeMo Evaluator | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) ![Agentic](https://img.shields.io/badge/Agentic-EF6C00?style=flat-square) | Benchmarks, LLM-as-judge, RAG and agent metrics | Bedrock Evaluations | Vertex Gen AI Evaluation | Foundry Evaluations | LangSmith Evals |
| ⭐ NeMo Guardrails + NemoGuard NIMs | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) ![GPU](https://img.shields.io/badge/GPU-76B900?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) ![Agentic](https://img.shields.io/badge/Agentic-EF6C00?style=flat-square) | Programmable rails (Colang) + content-safety, topic-control, jailbreak models | Bedrock Guardrails | Model Armor | Azure AI Content Safety, Prompt Shields | Guardrail middleware (PII, human-in-the-loop) |
| NeMo Auditor (garak) | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) | ![GenAI](https://img.shields.io/badge/GenAI-8E24AA?style=flat-square) | LLM vulnerability / red-team scanner | — | — | PyRIT | — |

## 10. Observability and licensing

| NVIDIA | Type | Domain | What it is | AWS | Google | Microsoft | LangChain |
|---|---|---|---|---|---|---|---|
| NAT profiler + OTel exporters (→ NeMo Relay) | ![NeMo](https://img.shields.io/badge/NeMo-1E88E5?style=flat-square) | ![Agentic](https://img.shields.io/badge/Agentic-EF6C00?style=flat-square) | Agent traces, token and latency profiling | CloudWatch / X-Ray, AgentCore Observability | Cloud Trace | Foundry tracing / App Insights | LangSmith |
| NVIDIA AI Enterprise | ![Platform](https://img.shields.io/badge/Platform-F9A825?style=flat-square) | ![All](https://img.shields.io/badge/All-9E9E9E?style=flat-square) | Paid license: support, security patches, NIM in production | — | — | — | LangSmith / Deployment plans |

## Takeaways

- LangChain only shows up in layers 7–10: it's an app framework, not infrastructure.
- Hyperscalers sell **managed services**; NVIDIA ships **portable containers** you run anywhere (including their clouds). NIM vs. Bedrock = control and data residency vs. zero ops.
- NVIDIA names were checked against live docs on 2026-10-29. Vendor-equivalent columns are a judgement mapping; verify a row before relying on it in an exam answer.

## Sources

- [NVIDIA Dynamo-Triton](https://developer.nvidia.com/dynamo-triton)
- [NVIDIA Dynamo](https://developer.nvidia.com/en-us/dynamo.md)
- [NeMo Microservices docs (sunset notice)](https://docs.nvidia.com/nemo/microservices/26.3.0/set-up/milvus.html)
- [NeMo Agent Toolkit GitHub (deprecation notice)](https://github.com/NVIDIA/NeMo-Agent-Toolkit)
- [NAT 1.4 release notes (integrations)](https://docs.nvidia.com/nemo/agent-toolkit/1.4/release-notes.html)
- [NAT CVE-2026-65145 write-up](https://aicybr.com/blog/nvidia-nemo-agent-toolkit-cve-2026-65145-patch-eol-migration)
- [LangServe repo (deprecation)](https://github.com/langchain-ai/langserve)
- [LangSmith Deployment](https://www.langchain.com/langsmith/deployment)
