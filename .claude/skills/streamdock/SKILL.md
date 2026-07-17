---
name: streamdock
description: Configure the StreamDock Hub device (app list, per-app keys, hotkeys) by editing profiles/*.yaml in this repo. Use whenever the user asks to add/remove apps or keys on their stream deck, change hotkeys, or reorganize the device layout. The running hub hot-reloads changes within ~1 second.
---

# StreamDock Hub configuration

The device UI is entirely defined by `profiles/*.yaml`. One file = one app on
the HOME view. Edit files directly; the hub daemon watches the directory and
redraws the device automatically — never tell the user to restart it.

## Profile schema
```yaml
name: slack            # required, lowercase, matches filename
label: Slack           # key label on the device
order: 4               # HOME sort position
match: Slack           # substring of window title/process for focus auto-switch
launch: {mac: "Slack", win: "slack.exe"}
voice_hotkey: {mac: "ctrl+alt+cmd+m", win: ""}   # app's own dictation hotkey, if any
big_knob_rotate: ""    # optional action on big-knob rotation in this app's view
keys:                  # MAX 6 (device has 6 LCD keys); keep Home last
  - {label: Dictate, action: voice_toggle}
  - {label: Search, action: {mac: hotkey cmd+k, win: hotkey ctrl+k}}
  - {label: Home, action: view HOME}
```

## Actions
`hotkey <combo>` | `type <text>` | `shell <cmd>` | `launch <app>` |
`voice_toggle` (universal dictation, types into focused field) |
`voice_app` (sends the profile's voice_hotkey, falls back to voice_toggle) |
`view HOME`.
Combos join with `+`: cmd, ctrl, alt/option, shift, enter, esc, space, tab, letters.
Any field may be per-OS: `{mac: ..., win: ...}`.

## Conventions
- Verify an app's real hotkeys before adding them (search if unsure); wrong
  combos silently do nothing or trigger the wrong thing.
- Keep a `Dictate` key on AI apps and a `Home` key last on every profile.
- Icons: optional 96x96 PNG in `icons/`, referenced as `icon: file.png`;
  otherwise a colored initial tile is auto-generated.
- 6-key limit is hard. If the user wants more, suggest splitting into two
  profiles or reassigning the small knobs (`knob1_rotate`, `knob2_rotate`).
