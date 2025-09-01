# Internet Archive WPI Helper — Starter (Tkinter)

Description
-----------
This is a starter Python/Tkinter GUI app that searches the Internet Archive for software items and helps you list and download candidate installer/archive files from those items. It's intended as a foundation for building an "Automatic Program Internet Archive Online Installer for WPI" (Windows Post-Install) project that can pull installers from the Internet Archive (Internet Arcade, Wayback Machine, software collection, etc.).

Compatibility & target
----------------------
- Designed to run on older Windows (Windows XP, Vista, 7, 8.1) if you use a compatible Python runtime:
  - Python 2.7 is the broadest compatibility for Windows XP.
  - Python 3.4 was the last Python 3 release with XP support; if you don't need XP you can use newer Python 3.x.
- The code uses only the Python standard library (no external dependencies) to ease packaging for old systems.

Files
-----
- main.py — The Tkinter GUI starter app (search, view, list files, download).

How it works (high level)
-------------------------
1. Uses the Internet Archive `advancedsearch` endpoint to find items in software collections.
2. Lists results (title and identifier).
3. Fetches item metadata via `https://archive.org/metadata/{identifier}` to enumerate files.
4. Presents candidate files (exe/msi/zip/7z/rar/iso by extension) and can download a selected file.
5. Uses background threads so GUI remains responsive.

Packaging for older Windows
---------------------------
- Python 2.7:
  - Use py2exe (legacy) to build an .exe — py2exe still works with 2.7.
  - Example: create a simple setup.py for py2exe and build.
- Python 3.x:
  - PyInstaller can build executables; older PyInstaller releases had better XP support than newest ones. Test on your target OS.
- After creating an exe, use Inno Setup (recommended) to create a redistributable installer.
- For WPI integration, you'll want to generate the appropriate XML or package definitions accepted by WPI.

Legal and ethical notes
-----------------------
- Be mindful of copyright and usage terms when downloading and redistributing installers from the Internet Archive.
- Some archived files may be copyrighted and not permitted for redistribution. Always check item licensing and permissions before automated distribution.

Next steps I can help with
--------------------------
- Add export to a WPI package list / XML format.
- Add a local cache (SQLite) of metadata and files to avoid repeated queries.
- Improve UI and user flow for automated install sequence (download -> signature/hash -> silent install commands).
- Implement per-item mapping: map archive items to WPI package entries (installer filename, silent args, uninstall command).
- Create packaging scripts for py2exe / PyInstaller and an Inno Setup template for target Windows versions.

Tell me:
- Which Python version do you want to target primarily (2.7 or a specific 3.x)?
- Do you already have a WPI schema you want to output, or should I propose one?
- Any additional integrations (Wayback Machine search, Internet Arcade emulator support, server-side job runner)?

I'll continue from your answers and implement the requested next features.
