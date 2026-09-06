# Chat widget latency notes

Measured 2026-09-06 against `main`, local Ollama 0.33.3 running `qwen3:4b`.

## The thing to check first: Ollama can silently drop to CPU and stay there

This is the headline, and it is worth more than any tuning in this document.

Ollama decides which compute device to use when its server process starts, and
it holds that decision for the life of that process. If the discrete GPU is
unavailable at that moment, for whatever reason, Ollama falls back to CPU
inference and keeps running on the CPU indefinitely. It does not retry. It does
not log an error the application can see. Every request still succeeds, and
every request is roughly five to six times slower.

From the application's side this is invisible. There is no exception, no error
field on the response, nothing in `views.py` or `ChatService` that could detect
it. It presents only as "the chat got slow", and it will stay that way until the
service is restarted.

**When chat latency is bad, restart the Ollama service before changing any code.**

Confirming which state you are in, from `/api/ps`:

- Healthy: `size_vram` is roughly equal to `size`, i.e. the model is resident on
  the GPU.
- Degraded: `size_vram` is `0`, and the server log says
  `msg="inference compute" id=cpu library=cpu`.

Both states were measured on this machine on the same day.

| | degraded (CPU) | healthy (GPU) |
| --- | --- | --- |
| decode rate | 8.3-10.9 tok/s | 49-52 tok/s |
| "What time is check-in?" | 35-50s | 6.2-9.7s |
| "How much is the 1 Bed With Balcony?" | not measured | 4.4-6.1s |
| "tell me about all room types" | 59-140s | 9.5-19.8s |
| worst observed | `ReadTimeout` at the 175s client timeout | 36.6s |

The healthy figures line up with the ~50 tok/s the provider module already
documents, and with the 11.6s median recorded in commit `c0dfb5f`. Nothing about
the application changed between the two rows above. Only the Ollama process did.

### Correction to an earlier draft of this document

An earlier version of these notes concluded that this machine had no usable GPU,
citing `Get-CimInstance Win32_VideoController` and an Ollama log line about
dropping an integrated Intel Iris Xe. That conclusion was wrong. It described a
transient state, not the hardware.

The machine has an **NVIDIA GeForce RTX 3060 Laptop GPU with 6143 MiB**, and
Ollama uses it:

```
llama_prepare_model_devices: using device CUDA0 (NVIDIA GeForce RTX 3060 Laptop GPU) - 5130 MiB free
load_tensors:        CUDA0 model buffer size =  2375.91 MiB
llama_kv_cache:      CUDA0 KV buffer size =   576.00 MiB
```

Restarting Ollama was the entire fix. Anything in that earlier draft that
depended on "inference runs on the CPU here" should be read as a description of
the degraded state only. In particular, the claim that
`REQUEST_TIMEOUT_SECONDS` was miscalibrated does not hold: it derives from
`TOKENS_PER_SECOND_FLOOR = 25`, which is correctly pessimistic against a real
50 tok/s. The `ReadTimeout` seen while degraded was a symptom of the fallback,
not a wrong constant.

## Two things that are actually wrong, independent of GPU state

Both survive the correction above. Neither is urgent, and neither is fixed here.

**1. `NUM_PREDICT_RETRY` is unreachable.** Ollama loads this model with
`n_ctx = 4096`. The DB-grounded system prompt is 874-882 tokens, so the most
that can ever be generated in one call is about 3,214 tokens. The retry budget
is set to 4,000. The second rung of the retry ladder does not fit in the context
window it runs in, so it can never be climbed as written.

**2. The retry ladder never fires anyway.** Across 13 warm samples covering four
question shapes, `done_reason` was `stop` every time. The highest `eval_count`
observed was 1,800 against a first-rung cap of 2,400. The ladder exists for a
failure mode that these measurements never reproduced.

## Tuning levers that were considered and rejected on evidence

Kept here so nobody re-runs these experiments.

**Trimming the DB-grounding context.** `ChatService.build_system_prompt()`
injects every room and service row with no limit, which looks like an obvious
target. It is not. The live data is 5 room types and 3 services, totalling 874
tokens, and warm prefill is already about 0.1s because llama.cpp caches the
prompt prefix. A differential test made things *worse*: cutting the prompt to
418 tokens pushed prefill from 0.101s to 10.681s, because changing the prefix
invalidated that cache. Trimming costs a one-off penalty and saves nothing after.

**Capping generation length.** `done_reason` was `stop` on every sample. The cap
is never reached, so lowering it saves nothing and risks truncating the longest
legitimate answers.

**Raising `keep_alive`.** Already 30m, already reaching Ollama, and
`load_duration` on warm requests is 0.004-0.007s. Nothing is being evicted.
Ollama's own default is 5m; the per-request value overrides the
`OLLAMA_KEEP_ALIVE` environment variable.

**Suppressing reasoning.** Not possible through request parameters on this
model. `qwen3:4b`'s chat template ends every prompt with an unconditional
`<think>` opener, so generation always begins inside a reasoning block.
Rendering the prompt with Ollama's debug render path shows `think=true`,
`think=false` and omitting the parameter produce byte-identical prompts. The
`think` flag only decides where the monologue is filed afterwards, which is why
`think=false` leaks it into `content`. Reasoning is 75-96% of everything
generated, and on a working GPU that is affordable.

## Answer quality

Checked alongside the timings, since a faster wrong answer is not an
improvement. On the healthy configuration, across three samples each: the price
question returned "1,150,000 VND per night" for the 1 Bed With Balcony every
time, matching the database, and the swimming pool question, which has no
supporting data, was declined and redirected to the front desk every time
rather than invented. No response leaked a `<think>` tag, and none was emptied
by `strip_thinking`.

## Caveats

Small samples on one machine: 13 warm generations in the healthy state, 7 in the
degraded state. Enough to separate buckets that differ by an order of magnitude,
not enough for a precise median. Run-to-run spread on an identical question
reached 29%, driven entirely by how many reasoning tokens the model happened to
emit. Treat the bucket split as solid and individual numbers as indicative.

Free system RAM differed between the two measurement sessions, 0.22-0.38 GB
while degraded against about 4 GB while healthy. That is worth knowing when
comparing the two tables, though it does not explain a 5x decode difference on
its own.
