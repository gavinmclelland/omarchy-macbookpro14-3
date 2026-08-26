# Spotify SIGTRAP on MacBookPro14,3

From sibling Grok diagnose-crash session, 2026-08-26 ~00:39 PDT.

Tracker: [#15](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/15).
This is **not** an Omarchy packaging bug. Do **not** file on `basecamp/omarchy`.

This file is sanitized: no Spotify account identifiers, no prefs/autologin blobs,
no core dump, no machine/boot IDs, no tracking protobufs.

## What crashed

| | |
| --- | --- |
| Process | `spotify` PID 67730, `/opt/spotify/spotify` |
| Package | `spotify 1:1.2.96.518-1` (Omarchy repo), first launch after install |
| Signal | `SIGTRAP` / `SI_KERNEL` at 2026-08-26 00:39:02 PDT |
| Runtime | 14 min 8 s, ~1.1 GiB peak |
| Memory | not OOM (~10 GiB available, swap unused) |
| Command | `/opt/spotify/spotify` — no `~/.config/spotify-flags.conf` |

Installed and opened via `omarchy-install-service-spotify` at 00:24. Stock
desktop wrapper; no extra CEF/Ozone flags.

## What the evidence proves

Crashing instruction is Chromium/CEF `ImmediateCrash` (`int3; ud2`) on the
**main thread** in bundled `/opt/spotify/libcef.so`.

The abort helper logs:

```
out_of_range was thrown in -fno-exceptions mode with message "string_view::substr"
```

Some CEF/UI code called `string_view::substr(pos)` with `pos > size()`. libc++
would throw `std::out_of_range`; CEF is `-fno-exceptions`, so the process
traps. Spotify ships no debuginfod for `libcef.so`. systemd-coredump’s unwind
goes through the CEF UI/message pump into Spotify `main`. Other threads were
idle (`poll` / `epoll` / `cond_wait`, GLib, Asio, PipeWire).

## Timeline (correlation, not a proven cause)

| Time | Event |
| --- | --- |
| 00:24:54 | first Spotify launch after install |
| 00:38:32 | `systemctl --user daemon-reload` from a terminal restarted PipeWire |
| 00:39:02 | SIGTRAP |
| 00:39:05 | Spotify relaunched |
| 00:40:34 | relaunch exited **without** a second coredump |

PipeWire had also been bounced at 00:24:00, 00:29:39, and 00:35:32 (user-unit
reloads). The abort is on the CEF UI thread, not the PipeWire thread (that one
was in `epoll_wait`). Inferring “audio graph change → UI string slice” is
plausible and **not proven**.

## Distinct from #2 (Chromium GPU)

Same boot also has two Chromium `SIGTRAP`s (22:59 and 23:04) during GitHub
device login. Those are `LOG(FATAL) GPU process isn't usable` on Polaris11
`renderD128` — already documented in `notes/chromium-gpu.md` / issue #2
(workaround `--disable-gpu`).

This Spotify dump is **not** that bug. It is a libc++ `string_view::substr`
bounds abort in CEF UI, not a GPU-process fatal.

Hardware acceleration had been on in the CEF profile. Dual GPU (Intel HD 630 +
AMD Polaris11) is background, not implicated by the crashing frame.

## Related to #14 (speakers / Spotify attach)

Issue #14 parked the 4ch crossover because Spotify could not play (`SiStandardLink`
failed; Spotify never attached to PipeWire). That failure mode was “can’t play
current song”, not a process abort.

This dump is a later, different failure: CEF abort ~30 s after a PipeWire
restart. Worth a comment on #14 for the timeline; worth its **own** issue for
the abort.

## User data

Nothing looks lost. Trash empty. Streaming library is server-side. Local cache
remains. Playback stopped with the process. Spotify was not running at diagnosis
time.

## Suggested GitHub issue

Title: `Spotify CEF abort: string_view::substr SIGTRAP after PipeWire restart`

Body: this file. Labels like `type:investigate` `area:audio` `phase:work`.
Comment on #14 with the 00:38:32 PipeWire bounce → 00:39:02 abort table.
Do not treat `--disable-gpu` as the fix unless a later dump shows the GPU path.

## Recurrence

One dump. Relaunch did not dump. Can recur on the same UI path. Workaround if
it loops: `~/.config/spotify-flags.conf` (e.g. `--disable-gpu`) is guesswork
here — proven fault is a string bounds check.
