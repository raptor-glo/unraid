#!/usr/bin/env python3
"""Make Raptor's Docker tab match docker-tab/layout.json.

    scripts/apply-docker-tab.py            # show what would change (default)
    scripts/apply-docker-tab.py --apply    # back up, then write it

It writes three files on Raptor over SSH (host alias "raptor", or $RAPTOR_HOST):
  /boot/config/plugins/folder.view2/docker.json   folders, icons, members
  /boot/config/plugins/dockerMan/userprefs.cfg    order of the Docker tab
  /var/lib/docker/unraid-autostart                start order and waits

Unraid starts containers in autostart-file order, so folder order is start
order. Which containers autostart is never changed here: only their order,
plus the waits in layout.json. Close the Docker tab in your browser before
--apply, or it can save its old layout back over this one.

Containers whose `folder.view2` label already names their folder are left out
of that folder's list (Folder View 2 adds them by label; listing them too
would show them twice).
"""
import argparse
import difflib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = os.environ.get("RAPTOR_HOST", "raptor")
FOLDERS_FILE = "/boot/config/plugins/folder.view2/docker.json"
PREFS_FILE = "/boot/config/plugins/dockerMan/userprefs.cfg"
AUTOSTART_FILE = "/var/lib/docker/unraid-autostart"


def ssh(cmd, stdin=None):
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, cmd],
                            input=stdin, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"✗ ssh {HOST} failed: {result.stderr.strip()}")
    return result.stdout


def read_remote(path):
    return ssh(f"cat '{path}' 2>/dev/null || true")


def containers_on_raptor():
    """{name: folder.view2 label or None} for every container, running or not."""
    out = ssh("docker ps -a --format '{{.Names}}\t{{.Label \"folder.view2\"}}'")
    found = {}
    for line in out.splitlines():
        name, _, label = line.partition("\t")
        found[name] = label or None
    return found


def build(layout, current_folders, current_autostart, containers):
    warnings = []
    placed = []
    default_settings = next(iter(current_folders.values()), {}).get("settings", {})
    base = layout["icon_base_url"]

    folders = {}
    for f in layout["folders"]:
        icon = ROOT / "icons" / f["icon"]
        if not icon.exists():
            sys.exit(f"✗ {f['name']}: icon {icon.relative_to(ROOT)} doesn't exist")
        members = []
        for c in f["containers"]:
            if c not in containers:
                warnings.append(f"{f['name']}: no container called {c!r} on Raptor (skipped)")
                continue
            placed.append(c)
            if containers[c] != f["name"]:  # labelled ones join by label
                members.append(c)
        old = current_folders.get(f["id"], {})
        folders[f["id"]] = {
            "name": f["name"],
            "icon": base + f["icon"],
            "settings": old.get("settings", default_settings),
            "regex": "",
            "containers": members,
            "actions": old.get("actions", []),
        }

    # Containers that carry a folder.view2 label for one of our folders count as placed.
    names = {f["name"] for f in layout["folders"]}
    for c, label in containers.items():
        if label in names and c not in placed:
            placed.append(c)
    unplaced = sorted(set(containers) - set(placed), key=str.lower)
    for c in unplaced:
        warnings.append(f"{c} isn't in any folder (added to the end of the tab)")

    # Tab order: each folder, then its containers in layout order.
    order = []
    for f in layout["folders"]:
        order.append(f"folder-{f['id']}")
        order += [c for c in f["containers"] if c in containers]
        order += [c for c, label in containers.items()
                  if label == f["name"] and c not in f["containers"]]
    order += unplaced
    prefs = "".join(f'{i}="{name}"\n' for i, name in enumerate(order))

    # Autostart: same set of containers, reordered to match, existing waits kept.
    waits = {}
    autostart = []
    for line in current_autostart.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] not in containers:
            warnings.append(f"autostart entry {parts[0]!r} has no container (dropped)")
            continue
        autostart.append(parts[0])
        if len(parts) > 1:
            waits[parts[0]] = parts[1]
    waits.update({k: str(v) for k, v in layout.get("start_wait_seconds", {}).items()})
    position = {name: i for i, name in enumerate(order)}
    autostart.sort(key=lambda c: position.get(c, len(position)))
    auto_text = "".join(f"{c} {waits[c]}\n" if c in waits else f"{c}\n" for c in autostart)

    return json.dumps(folders, separators=(",", ":")), prefs, auto_text, warnings


def show_diff(label, old, new):
    if old == new:
        print(f"= {label}: no change")
        return False
    print(f"~ {label}:")
    sys.stdout.writelines(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), "before", "after", n=1))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="back up and write the files")
    args = parser.parse_args()

    layout = json.loads((ROOT / "docker-tab" / "layout.json").read_text())
    raw_folders = read_remote(FOLDERS_FILE)
    current_folders = json.loads(raw_folders) if raw_folders.strip() else {}
    current_prefs = read_remote(PREFS_FILE)
    current_autostart = read_remote(AUTOSTART_FILE)
    containers = containers_on_raptor()

    new_folders, new_prefs, new_autostart, warnings = build(
        layout, current_folders, current_autostart, containers)

    # Show the folders file as readable JSON; it's written compact, as the plugin does.
    pretty = lambda s: json.dumps(json.loads(s), indent=1, ensure_ascii=False) + "\n" if s.strip() else ""
    changed = [
        show_diff("folders (docker.json)", pretty(raw_folders), pretty(new_folders)),
        show_diff("tab order (userprefs.cfg)", current_prefs, new_prefs),
        show_diff("autostart order", current_autostart, new_autostart),
    ]
    for w in warnings:
        print(f"! {w}")

    if not args.apply:
        print("\nDry run only. Close the Docker tab in your browser, then run with --apply.")
        return
    if not any(changed):
        print("Nothing to change.")
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    for path in (FOLDERS_FILE, PREFS_FILE, AUTOSTART_FILE):
        ssh(f"[ -f '{path}' ] && cp -a '{path}' '{path}.bak-{stamp}' || true")
    for path, text in ((FOLDERS_FILE, new_folders), (PREFS_FILE, new_prefs),
                       (AUTOSTART_FILE, new_autostart)):
        ssh(f"cat > '{path}'", stdin=text)
    print(f"\n✓ Applied. Backups end in .bak-{stamp}. Refresh the Docker tab to see it.")
    print(f"  Undo: for f in {FOLDERS_FILE} {PREFS_FILE} {AUTOSTART_FILE}; "
          f"do cp -a \"$f.bak-{stamp}\" \"$f\"; done")


if __name__ == "__main__":
    main()
