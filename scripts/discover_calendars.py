"""Discovery helper: list Outlook calendar GROUPS and the calendars inside them.

A "calendar group" (e.g. "Team: Terence Siew") contains one calendar per
person. This prints each group and its member calendars so we know exactly
what to point the connector at.

    python scripts/discover_calendars.py
"""
from __future__ import annotations

import win32com.client  # type: ignore

OL_MODULE_CALENDAR = 1
OL_FOLDER_CALENDAR = 9


def main() -> int:
    app = win32com.client.Dispatch("Outlook.Application")
    ns = app.GetNamespace("MAPI")

    explorer = app.ActiveExplorer()
    if explorer is None:
        explorer = app.Explorers.Add(ns.GetDefaultFolder(OL_FOLDER_CALENDAR), 0)
        explorer.Display()

    try:
        module = explorer.NavigationPane.Modules.GetNavigationModule(OL_MODULE_CALENDAR)
        groups = module.NavigationGroups
    except Exception as e:  # noqa: BLE001
        print(f"[!] Could not read the calendar navigation pane: {e}")
        print("    Make sure Outlook is open and showing the Calendar view.")
        return 1

    print("\n=== Calendar groups and their member calendars ===\n")
    for g in groups:
        print(f"GROUP: {g.Name!r}")
        try:
            nav_folders = g.NavigationFolders
        except Exception as e:  # noqa: BLE001
            print(f"   [could not list folders: {e}]")
            continue
        for nf in nav_folders:
            try:
                folder = nf.Folder
                store = folder.Store.DisplayName if folder.Store else "?"
                count = folder.Items.Count
                print(f"   - display={nf.DisplayName!r}  folder={folder.Name!r}  "
                      f"store={store!r}  items={count}")
            except Exception as e:  # noqa: BLE001
                print(f"   - display={getattr(nf, 'DisplayName', '?')!r}  [no folder: {e}]")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
