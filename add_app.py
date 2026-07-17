"""Interactive profile wizard: python add_app.py
Asks a few questions and writes profiles/<name>.yaml. Re-run the hub and the
app appears on the HOME view.
"""
import os
import yaml

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")


def ask(prompt, default=None):
    s = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return s or default or ""


def main():
    print("=== StreamDock Hub: add an app ===\n")
    name = ask("App id (lowercase, no spaces, e.g. obsidian)")
    label = ask("Label shown on the key", name.capitalize())
    match = ask("Window/process name to match for auto-switch", label)
    launch_mac = ask("macOS app name for 'open -a' (blank to skip)", label)
    launch_win = ask("Windows exe/command for 'start' (blank to skip)",
                     f"{name}.exe")

    keys = [{"label": "Dictate", "action": "voice_toggle"}]
    print("\nNow add hotkey keys (up to 4 more; blank label to finish).")
    print("Combos use: cmd/ctrl/alt/shift + letters, e.g. cmd+shift+p")
    while len(keys) < 5:
        klabel = ask(f"Key {len(keys)+1} label (blank = done)")
        if not klabel:
            break
        mac = ask("  macOS hotkey (blank = none)")
        win = ask("  Windows hotkey (blank = same as macOS)", mac)
        if mac == win:
            action = f"hotkey {mac}" if mac else ""
        else:
            action = {"mac": f"hotkey {mac}" if mac else "",
                      "win": f"hotkey {win}" if win else ""}
        keys.append({"label": klabel, "action": action})
    keys.append({"label": "Home", "action": "view HOME"})

    profile = {
        "name": name,
        "label": label,
        "match": match,
        "launch": {"mac": launch_mac, "win": launch_win},
        "keys": keys,
    }
    os.makedirs(PROFILE_DIR, exist_ok=True)
    path = os.path.join(PROFILE_DIR, f"{name}.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(profile, f, sort_keys=False, allow_unicode=True)
    print(f"\nWrote {path} — restart the hub (python run.py) to see it.")
    print("Optional: drop a 96x96 PNG in icons/ and add 'icon: file.png'.")


if __name__ == "__main__":
    main()
