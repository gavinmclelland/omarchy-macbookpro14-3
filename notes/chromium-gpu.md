# Chromium SIGTRAP on MacBookPro14,3

Chromium 151 aborted after `gh auth login --web`:

```
FATAL:content/browser/gpu/gpu_data_manager_impl_private.cc:417
GPU process isn't usable. Goodbye.
```

SIGTRAP / `ud2; int3` — `LOG(FATAL)`, not OOM.

Dual GPU: Intel HD 630 `i915` `renderD129` + AMD Polaris11 `amdgpu` `renderD128`.
ANGLE was on AMD (`radeonsi polaris11 ACO`, Mesa 26.2.1). GPU child unusable;
no i915/amdgpu hang in dmesg. Not an Omarchy bug.

Workaround applied 2026-08-25: `--disable-gpu` in `~/.config/chromium-flags.conf`
(after two SIGTRAPs during `gh auth login --web`). New Chromium windows pick it up.

Two dumps: PID 26211 22:59:43, PID 35128 23:04:49. Same `LOG(FATAL)`.
