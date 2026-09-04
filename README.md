
Default Folder X for Alfred
===========================


Show and search Default Folder X favourites and recent items in [Alfred][alfredapp].

**Note:** v0.3 and above are not compatible with Alfred 2. v0.4 and above require Python 3 (see [Requirements](#requirements)).


Requirements
------------

- Alfred 3.2 or later (the workflow uses the Script Filter *re-run* feature).
- [Default Folder X][stclair], installed and **running** — the workflow asks it
  for its favourites and recent items via AppleScript.
- Python 3 at `/usr/bin/python3`. On recent macOS versions this is provided by
  the Command Line Developer Tools (`xcode-select --install`). Python 2, which
  earlier versions of this workflow used, is no longer shipped with macOS.
- Permission for Alfred to control Default Folder X
  (*System Settings* → *Privacy & Security* → *Automation*). macOS asks the
  first time you run the workflow; if you decline, the workflow shows an error
  telling you what to fix.


Installation
------------

1. Download the latest `.alfredworkflow` from the [releases page][releases].
2. Open it to import the workflow into Alfred.
3. Launch Default Folder X before using the workflow.
4. The first time you run `dfx`, let Alfred control Default Folder X when
   macOS asks.


Usage
-----

- `dfx [<query>]` — Show/search all DFX favourite/recent items.
- `dfxf [<query>]` — Show/search only DFX favourite folders.
- `dfxr [<query>]` — Show/search only DFX recent files/folders.

In all three keywords:

- `↩` or `⌘+<NUM>` — Open in default application.
- `⌘+C` — Copy path to clipboard.
- `⌘+L` — Show path in Alfred's Large Type.
- `⇧` or `⌘+Y` — Quick Look the file/folder.
- `⌥+↩` (or Alfred's file actions) — Act on the file/folder.

In the combined `dfx` list, results are prefixed with ❤️ (favourite) or 🕞
(recent item).

Results are cached for a few seconds. If the cache is stale, the workflow
refreshes it in a background process and Alfred re-runs the Script Filter, so
the list updates live.


Troubleshooting
---------------

- If you see **“Default Folder X is not running”**, launch Default Folder X and
  try again.
- If you see an Automation-related error, re-enable Alfred under
  *System Settings* → *Privacy & Security* → *Automation*.
- v0.4.0 no longer self-updates; install newer releases manually from the
  [releases page][releases].


Licencing, thanks
-----------------

This workflow is released under the [MIT licence][mit].

The main workflow icon is the property of the [magnificent folks at St. Clair Software][stclair].

It was originally based on the [Alfred-Workflow][aw] library (MIT licence); as of v0.4.0 it has no third-party dependencies.

This bloody useful workflow would not exist but for [nickwild][nickwild].


Changelog
---------

### 0.4.0 ###

- Port to Python 3 (macOS no longer ships Python 2). See Alfred's note on
  [incompatible Python workflow libraries][incompat].
- Remove the bundled `Alfred-Workflow` and `docopt` libraries: `dfx.py` is now
  a self-contained script with no third-party dependencies. Caching, background
  jobs, fuzzy filtering, argument parsing and logging are built in.
- Script Filters run `/usr/bin/python3`.
- Emit Alfred's JSON Script Filter format (incl. `rerun` and Quick Look URLs).
- Show clear errors when Default Folder X isn't running or Alfred lacks
  Automation permission.
- Don't hide files under macOS privacy protection (Documents, Downloads, ...)
  when a permission error is mistaken for a missing path.
- Cache and log locations now follow Alfred's `alfred_workflow_cache` /
  `alfred_workflow_data` environment variables; the log file is `dfx.log`.
- Remove GitHub self-updating (`workflow:update` and friends are gone). Grab
  new releases from the [releases page][releases].

### 0.3.0 ###

- Remove update notification
- Use Alfred 3.2's re-run feature to update results when cached data are updated

### 0.2.0 ###

- Update folders in background
- Add auto-update info

### 0.1.0 ###

- First release


[mit]: ./src/LICENCE.txt
[aw]: http://www.deanishe.net/alfred-workflow/
[alfredapp]: https://www.alfredapp.com/
[stclair]: http://www.stclairsoft.com/
[nickwild]: http://www.alfredforum.com/topic/8695-default-folder-x/
[incompat]: https://www.alfredapp.com/help/troubleshooting/incompatible-python-workflow-library/
[releases]: https://github.com/deanishe/alfred-default-folder-x/releases
