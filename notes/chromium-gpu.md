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

## Recurrence: Spotify CEF (2026-08-26 16:43)

Issue [#2](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/2) **reopened**. Chromium flags do not cover other CEF apps.

`spotify` PID 9990, package `1:1.2.96.518-1`, SIGTRAP after 5h 36m. Not OOM. No
kernel GPU hang. `~/.cache/spotify/chrome_debug.log`:

```
[9990:9990:0826/164305.832544:FATAL:content/browser/gpu/gpu_data_manager_impl_private.cc:417] GPU process isn't usable. Goodbye.
```

Same FATAL line. No `spotify-flags.conf`. Distinct from [#15](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/15) (PID 67730 `string_view::substr`).

Intel cannot be the display GPU on this chassis: panel is `card1-eDP-1` (AMD);
i915 disabled its eDP. Visible BAR is 256 MiB of 4 GiB VRAM. `--disable-gpu` in
`~/.config/spotify-flags.conf` would be the same per-app bandaid; it is not applied
yet.
