# Serving layer — decision matrix (reference answers)

Companion to [nvidia-stack.md §4](nvidia-stack.md#4-serving-layer--decision-matrix). **H / M / L** = High / Medium / Low for that criterion. For *Hardware lock-in*, H is bad; for everything else, H is good.

> Snapshot as of Sep 2026. Pricing and project status change, so re-check NIM licensing and TGI's maintenance status before quoting them.

## Matrix


| Criteria                         | TensorRT-LLM (direct)                                       | Triton                                                                                         | Dynamo                                                   | NIM                                                                                   | vLLM                                                                   | SGLang                                                                | TGI                                       | llama.cpp / Ollama                        |
| -------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------- | ----------------------------------------- |
| **Peak throughput / latency**    | **H**: fastest on NVIDIA, esp. FP8/FP4 on Hopper/Blackwell  | **H**, but only as fast as its backend (TRT-LLM / vLLM)                                        | **H+ at scale**: prefill/decode split + KV-aware routing | **H**: pre-tuned TRT-LLM / vLLM / SGLang profiles                                     | **H**: close to TRT-LLM, sometimes level                               | **H**: best with shared prefixes / structured output (RadixAttention) | **M**                                     | **L**: single user, quantized             |
| **Time-to-first-deploy**         | **L–M**: engine build/config per GPU (`trtllm-serve` helps) | **L–M**: model repo + `config.pbtxt`                                                           | **L**: Kubernetes, etcd/NATS, operator                   | **H**: one `docker run`, OpenAI-compatible API                                        | **H**: `vllm serve <model>`                                            | **H**                                                                 | **H**                                     | **H+**: minutes                           |
| **Multi-model / non-LLM models** | **L**: LLMs (+ some VLMs) only                              | **H**: its reason to exist; ONNX, TensorRT, PyTorch, Python, ensembles, many models per server | **L–M**: LLM-focused                                     | **M**: broad catalog (embeddings, rerankers, speech, vision), one model per container | **M**: LLM, VLM, embeddings; one model per server                      | **M**                                                                 | **L–M**                                   | **M**: Ollama hot-swaps models; GGUF only |
| **Multi-node / disaggregated**   | **M**: TP/PP across nodes via MPI; some disaggregation      | **L–M**: not an orchestrator                                                                   | **H**: built for this                                    | **M**: multi-node NIMs for large models; disaggregation via Dynamo                    | **M**: Ray multi-node; disaggregation via connectors / llm-d / LMCache | **H**: mature P/D split, large expert-parallel deployments            | **L**                                     | **L**: experimental RPC only              |
| **Hardware lock-in**             | **H**: NVIDIA only; engines tied to GPU arch                | **M**: CPU + non-NVIDIA backends exist, but NVIDIA-first                                       | **M–H**: OSS, but NIXL/tuning NVIDIA-centric             | **H**: NVIDIA GPUs + NGC                                                              | **L**: NVIDIA, AMD, TPU, Gaudi, CPU, …                                 | **L–M**: NVIDIA, AMD; TPU emerging                                    | **L–M**                                   | **L**: runs almost anywhere               |
| **On-prem / air-gapped fit**     | **H**                                                       | **H**: proven in enterprises, incl. banks                                                      | **M**: OSS but heavy stack                               | **H** with NVIDIA AI Enterprise; offline model cache documented                       | **H**                                                                  | **H**                                                                 | **M**: maintenance mode = risk for a bank | **H dev / L prod**                        |
| **License / cost**               | Apache 2.0, free                                            | BSD-3, free (paid support via NVAIE)                                                           | Apache 2.0, free                                         | Free for dev/test; prod needs NVAIE (~$4.5k/GPU/yr list, verify)                      | Apache 2.0                                                             | Apache 2.0                                                            | Apache 2.0                                | MIT                                       |
| **Runs on my MacBook?**          | ❌ needs CUDA                                                | ⚠️ CPU-only in Docker, clunky                                                                  | ❌                                                        | ❌ locally; ✅ hosted NIMs at build.nvidia.com                                          | ⚠️ CPU / experimental Metal; fine for learning the API                 | ❌ in practice                                                         | ❌                                         | ✅ Metal, best Mac option (or MLX)         |




## How the pieces relate

- **TensorRT-LLM** is the *engine*. **Triton** (or `trtllm-serve`) is the *server* that exposes it.
- **Dynamo** is the *orchestration layer* above an engine (vLLM, SGLang or TRT-LLM): disaggregated prefill/decode, KV-aware routing, KV-cache transfer between GPUs.
- **NIM** is the *packaged, supported product*: you pay for NVIDIA AI Enterprise instead of tuning it yourself.



## Decision rules I'd defend in an interview

1. If it's **one LLM and I need portability across GPU vendors**, use **vLLM** (or **SGLang** for prefix-heavy / agentic workloads) because they're H on throughput and L on lock-in.
2. If I need the **lowest cost per token on NVIDIA at large scale**, use **TRT-LLM behind Dynamo** because the prefill/decode split and KV-aware routing raise GPU utilization beyond what a single engine gets.
3. If I'm serving a **mixed fleet (fraud-scoring models, ONNX/XGBoost, embeddings and LLMs together)**, use **Triton** because it's the only option rated H on multi-model / non-LLM.
4. If the enterprise wants **a vendor contract, support SLAs and fast time-to-value**, use **NIM** because it's H on time-to-first-deploy and on-prem fit, and the license buys the support.
5. If it's a **new production system at a regulated bank**, **don't** use **TGI** because it's in maintenance mode and long-term patching is uncertain.



## My lab environment

- **MacBook:** Ollama / llama.cpp for local work; hosted NIM endpoints (build.nvidia.com) to learn the NIM API.
- **RunPod (L4 default, H100 for FP8 days):** TRT-LLM, Triton, Dynamo, self-hosted NIM, vLLM and SGLang labs (`labs/tensorrt-llm`, `labs/triton-dynamo`, `labs/nim`).


---

# Day 25 (W04 D06): engine room: NIM, Dynamo-Triton, TensorRT-LLM

![NIM, TRT-LLM, Triton and Dynamo: who does what](img/w04d06-m1-serving-layers.svg)

*Editable source: [w04d06-m1-serving-layers.excalidraw](img/w04d06-m1-serving-layers.excalidraw)*

## §1 Bets

| Bet | Prompt | Guess | Actual | Result |
|---|---|---|---|---|
| A | KV cache reserves 4,096 tokens/slot, average request uses 768: % wasted | 81% | **81%** (1 − 768/4096) | win |
| B | Speculative decoding speeds things up most at… | the same at both | **batch 1** | miss |
| C | Versions `1/` and `2/`, no `version_policy`: what's served? | neither: refuses to load | **only 2** (default = latest, n = 1) | miss |
| D | `max_batch_size: 32`, 2 GPU instances: concurrency for max throughput | 64 | **128** (2 × 32 × 2) | miss |

Score: 1/4. Misses logged in [gap-log.md](gap-log.md).

## §2 NIM

- **At startup NIM does:** detects the GPU, picks **exactly one** pre-validated profile (`<backend>-<precision>-tp<N>-pp1[-lora]`, e.g. `vllm-bf16-tp1-pp1`), downloads only that profile's files into the cache (`/opt/nim/.cache`), starts the engine and exposes OpenAI-compatible `/v1/chat/completions`, `/v1/completions`, `/v1/responses` plus health endpoints. Inside: `nim-llm` (orchestration, LoRA, health proxy), `nimlib` (licensing, profile selection, downloads), the inference engine.
- **You still own:** the GPU and driver, the cache volume (or every restart re-downloads), scaling and routing, and the licence (Production Branch needs **NVIDIA AI Enterprise**; plain NIM is free for dev/research under its terms).
- **Pin `NIM_MODEL_PROFILE`** when you need reproducibility across nodes (same profile everywhere, same numbers in a benchmark), when auto-select picks a *Low memory* profile and you'd rather run a smaller `--max-model-len` on purpose, or when an air-gapped cache only holds one profile.
- NIM 2.x is *one container, one backend* (built on vLLM); profile names still carry the backend tag. NIM 1.x bundled TRT-LLM / vLLM / SGLang in one image.
- **Multi-LoRA:** one base model in GPU memory, many adapters on top; `/v1/models` lists them and the request's `model` field picks one. For an agent team where triage, investigator and report writer each have a fine-tune, that's one GPU footprint instead of three deployments.
- **Glossary:** **NGC**: NVIDIA's catalog of GPU-optimized containers, models, Helm charts and NIMs (`nvcr.io`). **NVIDIA AI Enterprise**: the licensed suite with enterprise support and security maintenance. **Base Command**: NVIDIA's software to manage and schedule AI workloads on DGX. **DGX**: NVIDIA's integrated multi-GPU AI systems (DGX Cloud rents them; it backs build.nvidia.com).

**The API your agent already uses.** Tool calling on a self-hosted NIM needs two engine args passed to `nim-serve`: `--enable-auto-tool-choice` and `--tool-call-parser llama3_json`. Day 4's [`verdict.py`](../app/tools/verdict.py) sends `extra_body={"guided_json": Verdict.model_json_schema()}` to the hosted endpoint. On a self-hosted NIM 2.x (vLLM ≥ 0.12 passthrough, no `nvext`) `guided_json` is gone: send `response_format={"type": "json_schema", "json_schema": {"name": "verdict", "schema": Verdict.model_json_schema()}}` (or vLLM's `structured_outputs: {"json": schema}`). Same idea: constrained decoding to a schema.

## §3 TensorRT-LLM

> Current TRT-LLM: the TensorRT engine backend is removed, **PyTorch is the only backend**, no `convert_checkpoint.py` / `trtllm-build`: `LLM(model="<hf_model>")` or `trtllm-serve <hf_model>`. The old build flow is exam history.

| Lever | What it does | Saves |
|---|---|---|
| **In-flight batching** | Re-forms the batch every iteration: finished requests leave, waiting ones join, prefill runs alongside decode; decode requests scheduled first | **Throughput** (GPU stays busy, nobody waits for the slowest request) |
| **Paged KV cache** | KV in fixed blocks (default 32 tokens) handed out on demand instead of `max_seqlen` per slot | **Memory** (→ more concurrent requests) |
| **KV / prefix reuse** | Filled blocks go in a radix tree; a request with a matching prefix reuses them | **Prefill compute + memory** → lower TTFT |
| **Chunked prefill** | Splits a long prompt's context phase into chunks interleaved with decodes | **Latency** for other users (no long stalls), steadier ITL |
| **Speculative decoding** | Cheap drafter proposes tokens, target verifies them in one pass | **Latency** at **low batch** only (no dynamic disable) |
| **Quantization FP8 / INT8 / INT4** | Fewer bits for weights (and KV) | **Memory** and **throughput**; FP8 on Hopper/Blackwell keeps accuracy best |
| **Disaggregated serving** | Prefill and decode on different GPUs, each with its own parallelism | **Latency** (prefill no longer delays others' tokens) + per-phase sizing |

- **The planner's 2,000-token system prompt on every call → KV / prefix reuse.** The same prefix's blocks are already in the radix tree, so prefill only runs on the new tokens: lower TTFT and less KV memory per request.
- **KV math:** 32 layers × 8 KV heads (GQA) × 128 head_dim × 2 (K and V) × 2 B = **128 KiB/token** → 512 MiB per 4,096-token sequence. Contiguous cache at 768/4,096 used = 81% wasted; paged wastes at most one partly-filled block per sequence.
- **Medusa vs EAGLE:** Medusa adds extra decoding **heads** to the target (each predicts a token further ahead), no separate draft model; EAGLE drafts from the target's hidden states with a small trained draft head. Draft/target needs a shared tokenizer.
- **Side quest (NeMo Performance Tuning Guide):** FP8 recipe covers linear layers only, ~1.2–1.5× over BF16, less on small models. **TP stays inside the NVLink domain** because tensor parallelism does an all-reduce after every layer: crossing to InfiniBand/Ethernet makes every layer wait on the slow link. Same for a self-hosted engine's TP size.

## §4 Dynamo-Triton

- **Dynamo-Triton = Triton Inference Server, renamed.** Multi-framework (TensorRT, PyTorch, ONNX, OpenVINO, Python, RAPIDS FIL), dynamic batching, concurrent execution, Prometheus metrics. **NVIDIA Dynamo** is the separate LLM framework (disaggregated serving, KV-aware routing, KV offload).
- **Ports:** **8000** HTTP · **8001** gRPC · **8002** Prometheus metrics.
- Repository: `tritonserver --model-repository=<path>`; one folder per model, optional `config.pbtxt`, **≥ 1 numeric version folder**. Version policy default = `latest { num_versions: 1 }`.
- Annotated config: [`labs/triton-dynamo/model-repo/alert_classifier/config.pbtxt`](../labs/triton-dynamo/model-repo/alert_classifier/config.pbtxt).
- **Schedulers:** **dynamic batcher** = stateless models (BERT, CNNs, this classifier), batches requests. **Sequence batcher** = stateful models: every request of a sequence lands on the same instance with start/end/ready signals. **Ensemble scheduler** = a fixed DAG of models in config (tokenizer → model → post-processing). **BLS** = Python-backend code that calls other models with loops/if-else. **TRT-LLM backend** = its own iteration-level **in-flight batcher** (`batching_strategy: inflight_fused_batching`, `batch_scheduler_policy` = `guaranteed_no_evict` default or `max_utilization`), streaming needs `decoupled_mode: true`.
- **`max_queue_delay_microseconds: 100` at concurrency 1:** there's never company, so every request waits the full 100 µs for nothing: a tiny latency cost, zero gain. It only pays off under load, when it lets partial batches fill.
- Tuning: Perf Analyzer first; min latency = concurrency 1, no batcher, 1 instance; max throughput = concurrency **2 × max batch × instances** (64 for 1 instance, 128 for this config). A sweep that stops at 32 only sees the rising part of the curve.

## §5 Decision matrix

KV per token = 2 × layers × (heads × head_dim) × bytes (NVIDIA blog: Llama 2 7B ≈ 2 GB KV per 4K sequence on top of 14 GB weights).

| Option | Time to production | Latency control | Ops burden | Licence / support | When the exam wants it |
|---|---|---|---|---|---|
| **Hosted NIM (build.nvidia.com)** | Minutes: an API key | None | None | Free trial credits; NVIDIA runs it | Prototyping, eval, no GPUs, data may leave |
| **Self-hosted NIM** | Hours: `docker run` / Helm, auto-picked optimized profile | Medium: pin profile, engine args | Low–medium: GPU, cache, scaling | Free for dev; **AI Enterprise** for production support | "Fastest path to production" on your own GPUs, OpenAI-compatible |
| **TRT-LLM + Dynamo-Triton** | Days: config, tuning | **Highest**: FP8, IFB policy, KV reuse, spec decoding | High | Open source (Apache / BSD); support via AI Enterprise | "Lowest latency / max throughput on NVIDIA", mixed model fleets |
| **vLLM** | Hours: `vllm serve` | Medium–high | Medium | Apache 2.0, community | Portability across GPU vendors, open source |
| **NVIDIA Dynamo** | Days–weeks: K8s, operators | Highest at scale: disaggregated P/D, KV-aware routing | Highest | Apache 2.0 | Multi-node, large-scale LLM serving, cost per token at scale |

## §6 Two scenarios

- **Lowest latency for the planner on H100s:** TensorRT-LLM behind Dynamo-Triton (or Dynamo at scale). Config: **FP8** weights + KV on H100, **KV/prefix reuse** for the shared system prompt, **speculative decoding** (EAGLE 3) since planner calls are low-batch, `max_utilization` off (keep `guaranteed_no_evict`) so started plans don't stall. Most control, most work.
- **Fastest path to production, same model:** **self-hosted NIM**. It picks an optimized profile for the GPU, ships health endpoints and an OpenAI-compatible API, so the agent code only changes `NIM_BASE_URL`. Different answer because the question optimizes engineering time, not milliseconds.
- **Customer data can't leave the EU:** hosted build.nvidia.com is out. Self-hosted NIM, TRT-LLM + Triton, vLLM and Dynamo all survive if they run in an EU region / on-prem.

## §7 Self-hosted run (Day 30)

> **Not run yet:** needs a Brev L40S instance in VM mode (≈ 75 min cap; check the hourly price in the console first). Commands from the guide, condensed:

```bash
docker run --rm --gpus all ubuntu nvidia-smi -L
echo "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin
export NIM_IMAGE=nvcr.io/nim/meta/llama-3.1-8b-instruct:2.0.13
docker run --rm --gpus all $NIM_IMAGE list-model-profiles | tee ~/profiles_l40s.txt
export LOCAL_NIM_CACHE=~/.cache/nim && mkdir -p "$LOCAL_NIM_CACHE"
docker run -d --name nim --gpus all -u $(id -u) -e NGC_API_KEY -e NIM_MODEL_PROFILE=vllm-bf16-tp1-pp1 \
  -v "$LOCAL_NIM_CACHE:/opt/nim/.cache" -p 8000:8000 $NIM_IMAGE \
  nim-serve --enable-auto-tool-choice --tool-call-parser llama3_json
until curl -sf localhost:8000/v1/health/ready > /dev/null; do sleep 10; done; date
uvx aiperf profile --model meta/llama-3.1-8b-instruct --tokenizer unsloth/Meta-Llama-3.1-8B-Instruct \
  --url http://localhost:8000 --endpoint-type chat --streaming --concurrency 8 --request-count 64
# laptop: brev port-forward <instance> --port 8000:8000, then
# NIM_BASE_URL=http://localhost:8000/v1 AGENT_MODEL=meta/llama-3.1-8b-instruct uv run python app/tools/agent.py "Alert A-1001: ..."
```

| | Value |
|---|---|
| GPU | L40S 48 GB (the L4 isn't on this model's support matrix) |
| Compatible profiles (`list-model-profiles`) | |
| Pinned profile | `vllm-bf16-tp1-pp1` |
| Minutes `docker run` → `/v1/health/ready` (empty cache) | |
| Cache size (`du -sh ~/.cache/nim`) | |
| AIPerf @ concurrency 8: TTFT p50 / p99 | |
| Inter-token latency p50 | |
| Output tokens/s | |
| Agent on the self-hosted NIM: answer correct? tool calls parsed? | |
| Session cost | |

- **What the cache volume saves:** the next start skips the multi-GB download and only loads weights, so readiness goes from minutes to roughly the model-load time. Without the volume, every restart (or every new pod) pays the download again.
- **Which metric the planner cares about:** **TTFT** dominates for an agent: each step is a short tool-call JSON, so time to the first token (prefill + queueing) is most of the call; ITL matters for long final reports; tokens/s is the capacity number for the whole team.
- **When self-hosting beats the hosted API:** steady high volume (a reserved GPU is cheaper per token than per-call pricing), data that can't leave the bank or the region, latency control (pinned profile, prefix reuse, no shared queue), and model choice (fine-tunes, multi-LoRA). For bursty dev and eval work, the hosted API wins.
