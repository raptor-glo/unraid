# Raptor (Unraid) config

Raptor's Docker tab, kept as code and applied from the studio VM.

```
docker-tab/layout.json        folders: order, names, icons, members, start waits
icons/folders/                folder icons in use, named after their folder, 128 px
icons/spare/                  icons kept for later, as downloaded
icons/CREDITS.md              where each icon came from
scripts/add-icon.sh           store an icon you downloaded as a folder icon
scripts/apply-docker-tab.py   make Raptor's Docker tab match layout.json
```

This repo is public because the Docker tab loads the icons from
`raw.githubusercontent.com`. Keep anything private out of it.

## How the Docker tab works

- **Folders** come from the [Folder View 2](https://github.com/VladoPortos/folder.view2) plugin.
- **Folder order is start order.** Unraid starts containers in the order of
  the Docker tab, so `Network` goes first: eight containers (the *arrs,
  downloaders, flaresolverr, brave) use `gluetunVPN`'s network and can't
  start without it. `gluetunVPN` gets a 15-second head start
  (`start_wait_seconds`).
- **Autostart on or off** stays a per-container switch in Unraid. The apply
  script only reorders it.

## Changing things

Run these on the studio, in `~/code/unraid`:

1. **New folder icon**: download the icon you want (Flaticon's animated
   icons, GIF), and get it onto the studio in any of these ways:
   - drop it into a Claude session on the studio and say which folder it's for;
   - `scp ~/Downloads/icon.gif studio:inbox/` from a Mac;
   - upload it to `icons/inbox/` on GitHub (works from a phone).

   Then `scripts/add-icon.sh <file> <folder-name> "<author>, Flaticon"`. It
   resizes GIFs to 128 px, keeping every frame, names the file after the
   folder, and records the credit. Free Flaticon icons need the author's name.
2. **Move or add a container**: edit `docker-tab/layout.json`.
3. Commit and push. Icons load from GitHub, so push before applying.
4. `scripts/apply-docker-tab.py` shows the changes. Close the Docker tab in
   your browser, then `scripts/apply-docker-tab.py --apply`, then refresh
   the Docker tab. Each apply backs up the three files on Raptor first
   (`*.bak-<time>`) and prints the command to undo it.

## Toy Soldier Studios apps

Studio apps join their folder by label, so they don't need adding to
`layout.json`. Each container in an app's `docker-compose.yml` gets:

```yaml
labels:
  folder.view2: "Toy Soldier Studios"
  net.unraid.docker.icon: "http://192.168.68.121:<app port>/pwa-192x192.png"
```

The icon is the app's own favicon artwork, served by the app, so it always
matches. When an app has more than about three containers, give it its own
folder: add one to `layout.json` and change that app's `folder.view2` label.
