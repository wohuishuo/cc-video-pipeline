# Qwen3-TTS 在 Intel Arc 130T (XPU) 上的加速实验结论

实验日期：2026-06-21。目标：让纳西妲克隆配音从 CPU 提速到 GPU。

## TL;DR

**这块卡 + 这个模型，单纯切 XPU 没有加速（和 CPU 一样 ~0.30x 实时）。** 要拿到传说中的
6.5x 必须上 `torch.compile`(inductor) + 形状 bucket + 手写解码循环那整套（fork 做的），
工程量大且脆弱、还绑死 transformers 5.x。当前结论：**继续用 CPU，多进程并行榨核**。

## 关键发现

### 1. XPU 加载崩溃的真凶不在 qwen_tts，在 transformers
```
transformers/modeling_utils.py:6090  caching_allocator_warmup
  -> torch.xpu.mem_get_info(index)
  -> RuntimeError: The device (Intel Arc 130T) doesn't support querying free memory
```
对应 pytorch issue #161403。这是**加载阶段**就崩，跟 generate 无关。

**干净修法**（加载前 monkeypatch，无害，只是预分配提示）：
```python
if torch.xpu.is_available():
    _GB = 16 * 1024**3
    _o = torch.xpu.mem_get_info
    def _safe(d=None):
        try: return _o(d)
        except Exception: return (_GB, _GB)
    torch.xpu.mem_get_info = _safe
```
加这一个 shim 后，**原版 qwen_tts 的 generate 路径在 XPU 上直接能跑通**，
不需要第三方 fork 的手写解码循环（那是 transformers 5.x 适配 + compile 友好用的）。

### 2. 实测速度（同一句中文，纳西妲克隆，热运行稳态）
| 配置 | RTF | 说明 |
|---|---|---|
| CPU fp32 | 0.30x | 基线 |
| XPU bf16（裸切设备）| 0.30x | **零加速** |
| XPU bf16 + torch.compile(default) | 0.18~0.28x | **更慢**，形状抖动反复重编译 |

### 3. 为什么 XPU 不快
- 模型只有 0.6B，**自回归逐 token**，每 token 一次 kernel 启动+同步
- flash-attn 在 XPU 上没有 → 退回 eager 注意力（很慢）
- 小计算量下，XPU 的 kernel 启动开销盖过算力收益
- 6.5x 来自 inductor 编译消除启动开销，但需固定形状（bucket padding）否则重编译抖动

## 第三方 fork 评估：allanmeng/ComfyUI-Qwen3TTS-XPU
- 思路对（XPU + torch.compile + bucket padding），但**针对 transformers 5.x 写的**
- 直接装会崩：`check_model_inputs`/`auto_docstring(custom_args=)`/`merge_with_config_defaults`
  都是 5.x API，我们是 4.57.3
- 真正 XPU 必需的改动其实很少（device= 放置 + mem_get_info），大头是 compile 配套

## 当前采用的方案
CPU 多进程并行：14 核开 2 个进程、每个 `OMP_NUM_THREADS=7`，
把 6 个 Part 的配音分两路同时跑，约对半砍总时长。

## 补充实测（装完 MSVC cl.exe 之后，2026-06-21 晚）
装了 Visual Studio 2022 BuildTools 的 VCTools(cl.exe 14.44)，inductor 终于能编译：
- `torch.compile(model.model.talker, backend="inductor")` **成功编译，不再报错**
- 但 **没有 bucket padding，每个不同长度的段都触发重编译** → 第一个真实条目反而要 36s（比 CPU 还慢）
- 预热短句 28→10→15s 也是形状抖动重编译的表现
- **结论：cl.exe 是 compile 生效的必要条件（已补齐），但还不充分——必须再加 bucket padding 把输入 padding 到固定形状，compile 才能真正快起来。** 这块是 fork 的 tokenizer 改动里那段(BUCKET=64 的 chunked_decode + 固定 talker 输入长度)，但和 transformers 5.x 不兼容代码缠在一起，要单独摘出来移植。

脚本 `synth_gpu.py` 已写好(XPU+compile+预热+cache_clean+max_new_tokens封顶)，`run_gpu.ps1` 激活 vcvars。
差最后一步 bucket padding 才能拿到 4.6x。

## 如果以后要认真做 XPU 提速（剩余步骤）
1. ~~装 C++ 编译器~~ ✅ 已装 MSVC BuildTools cl.exe
2. 移植 fork 的 bucket padding：talker 输入 padding 到固定桶长 + chunked_decode 的 BUCKET=64
3. 可选 `torch.compile(dynamic=True)` 先试单图动态形状，省掉 bucket 移植
4. 在 lab 验证音质无损再上生产

## 跑飞(无限复读)保护 —— 已落地
TTS 偶尔在数字密集长句上无限复读(part2 的 D11 单段跑了 11 分钟)。
synth.py / synth_gpu.py 都加了 `max_new_tokens=600`(~50s 硬上限) + 超长重采样。
实测 D11 从 655s 封到正常 18s。
