#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Internet Archive WPI helper - minimal starter Tk GUI
Supports Python 2.7 and Python 3.x (aimed at compatibility for older Windows)
Features:
- Search Internet Archive for software items
- List results and open item page in browser
- Fetch item metadata and list candidate files (exe, msi, zip, 7z, rar)
- Download a selected file with a simple progress indicator

NOTE: This is a starting scaffold. Improve error handling, UI polish, and integrate with WPI export as needed.
"""

from __future__ import print_function, unicode_literals

import sys
import os
import threading
import time
import json

try:
    # Python 3
    import tkinter as tk
    import tkinter.ttk as ttk
    import tkinter.filedialog as filedialog
    import tkinter.messagebox as messagebox
    from urllib.parse import urlencode, quote_plus
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    from queue import Queue, Empty
except Exception:
    # Python 2
    import Tkinter as tk
    import ttk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    from urllib import urlencode, quote_plus
    from urllib2 import urlopen, Request, URLError, HTTPError
    from Queue import Queue, Empty

import webbrowser

# Basic config
SEARCH_ROWS = 40
IA_ADV_SEARCH = "https://archive.org/advancedsearch.php"
IA_METADATA = "https://archive.org/metadata/{identifier}"
IA_ITEM_PAGE = "https://archive.org/details/{identifier}"
IA_DOWNLOAD = "https://archive.org/download/{identifier}/{file}"

# File suffixes we consider as installers/archives
CANDIDATE_SUFFIXES = (".exe", ".msi", ".zip", ".7z", ".rar", ".iso")

# Util: fetch url and return decoded JSON or raw bytes
def fetch_url(url, headers=None, timeout=30):
    try:
        req = Request(url, headers=headers or {})
        resp = urlopen(req, timeout=timeout)
        data = resp.read()
        # Python3 -> bytes, decode when used as text
        return data
    except HTTPError as e:
        print("HTTPError:", e)
        raise
    except URLError as e:
        print("URLError:", e)
        raise

def search_archive(query, rows=SEARCH_ROWS):
    """
    Use Internet Archive advancedsearch to find software items.
    Returns JSON-parsed results or raises.
    """
    q = 'collection:(software OR "opensource_software") AND ({q})'.format(q=query)
    params = {
        "q": q,
        "fl[]": ["identifier", "title", "creator", "description"],
        "rows": rows,
        "output": "json",
    }
    # Build query manually to support multiple fl[] keys in older py versions
    qs_parts = []
    for k, v in params.items():
        if isinstance(v, (list, tuple)):
            for item in v:
                qs_parts.append(quote_plus(k) + "=" + quote_plus(item))
        else:
            qs_parts.append(quote_plus(k) + "=" + quote_plus(str(v)))
    qs = "&".join(qs_parts)
    url = IA_ADV_SEARCH + "?" + qs
    raw = fetch_url(url)
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return json.loads(raw)
    except Exception:
        print("Failed to parse JSON from search")
        raise

def get_item_metadata(identifier):
    url = IA_METADATA.format(identifier=quote_plus(identifier))
    raw = fetch_url(url)
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return json.loads(raw)
    except Exception:
        print("Failed to parse metadata JSON for", identifier)
        raise

# Downloader thread function
def download_file(identifier, filename, target_path, progress_callback=None):
    url = IA_DOWNLOAD.format(identifier=quote_plus(identifier), file=quote_plus(filename))
    try:
        req = Request(url, headers={})
        resp = urlopen(req, timeout=60)
        total = resp.headers.get("Content-Length")
        if total:
            total = int(total)
        dest = os.path.join(target_path, filename)
        with open(dest, "wb") as fh:
            chunk_size = 8192
            downloaded = 0
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                fh.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)
        return dest
    except Exception as e:
        print("Download error:", e)
        raise

# UI application
class App(object):
    def __init__(self, root):
        self.root = root
        root.title("Internet Archive WPI Helper - Starter")
        self.build_ui()
        self.results = []
        self.queue = Queue()

        # Periodic queue check
        self.root.after(200, self._poll_queue)

    def build_ui(self):
        frm = ttk.Frame(self.root, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)

        search_row = ttk.Frame(frm)
        search_row.pack(fill=tk.X, pady=4)
        ttk.Label(search_row, text="Search query:").pack(side=tk.LEFT)
        self.query_var = tk.StringVar()
        self.query_entry = ttk.Entry(search_row, textvariable=self.query_var, width=50)
        self.query_entry.pack(side=tk.LEFT, padx=6)
        self.search_btn = ttk.Button(search_row, text="Search", command=self.on_search)
        self.search_btn.pack(side=tk.LEFT, padx=4)

        # Results list
        list_row = ttk.Frame(frm)
        list_row.pack(fill=tk.BOTH, expand=True)
        self.listbox = tk.Listbox(list_row, height=15)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        sb = ttk.Scrollbar(list_row, orient=tk.VERTICAL, command=self.listbox.yview)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.config(yscrollcommand=sb.set)

        # Details and actions
        details = ttk.Frame(frm)
        details.pack(fill=tk.X, pady=6)
        self.details_text = tk.Text(details, height=6, wrap=tk.WORD)
        self.details_text.pack(fill=tk.X, expand=True)
        self.details_text.config(state=tk.DISABLED)

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X, pady=2)
        self.open_btn = ttk.Button(btn_row, text="Open in Browser", command=self.on_open, state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT, padx=4)
        self.fetch_files_btn = ttk.Button(btn_row, text="List Candidate Files", command=self.on_list_files, state=tk.DISABLED)
        self.fetch_files_btn.pack(side=tk.LEFT, padx=4)
        self.download_btn = ttk.Button(btn_row, text="Download Selected File", command=self.on_download, state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=4)

        self.progress_label = ttk.Label(frm, text="")
        self.progress_label.pack(fill=tk.X)

        files_row = ttk.Frame(frm)
        files_row.pack(fill=tk.X, pady=4)
        ttk.Label(files_row, text="Candidate files:").pack(side=tk.LEFT)
        self.files_var = tk.StringVar(value=[])
        self.files_combo = ttk.Combobox(files_row, textvariable=self.files_var, state="readonly")
        self.files_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

    def _poll_queue(self):
        try:
            while True:
                func, args = self.queue.get_nowait()
                try:
                    func(*args)
                except Exception as e:
                    print("Queue task error:", e)
        except Empty:
            pass
        self.root.after(200, self._poll_queue)

    def on_search(self):
        q = self.query_var.get().strip()
        if not q:
            messagebox.showinfo("Enter query", "Please enter a search query.")
            return
        self.search_btn.config(state=tk.DISABLED)
        self.progress_label.config(text="Searching...")
        t = threading.Thread(target=self._background_search, args=(q,))
        t.daemon = True
        t.start()

    def _background_search(self, query):
        try:
            res = search_archive(query)
            docs = res.get("response", {}).get("docs", [])
            # Put result to queue for main thread UI update
            self.queue.put((self._on_search_complete, (docs,)))
        except Exception as e:
            self.queue.put((self._on_search_error, (e,)))

    def _on_search_complete(self, docs):
        self.results = docs
        self.listbox.delete(0, tk.END)
        for d in docs:
            title = d.get("title") or "(no title)"
            ident = d.get("identifier") or ""
            display = u"{t} — {id}".format(t=title, id=ident)
            self.listbox.insert(tk.END, display)
        self.progress_label.config(text="Search complete: {} results".format(len(docs)))
        self.search_btn.config(state=tk.NORMAL)

    def _on_search_error(self, err):
        messagebox.showerror("Search failed", str(err))
        self.progress_label.config(text="Search error")
        self.search_btn.config(state=tk.NORMAL)

    def on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            self.open_btn.config(state=tk.DISABLED)
            self.fetch_files_btn.config(state=tk.DISABLED)
            return
        idx = sel[0]
        item = self.results[idx]
        ident = item.get("identifier", "")
        title = item.get("title", "(no title)")
        desc = item.get("description", "")
        text = u"Title: {t}\nIdentifier: {id}\n\n{d}".format(t=title, id=ident, d=(desc or ""))
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, text)
        self.details_text.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.NORMAL)
        self.fetch_files_btn.config(state=tk.NORMAL)
        self.files_combo['values'] = []
        self.download_btn.config(state=tk.DISABLED)

    def on_open(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        ident = self.results[idx].get("identifier")
        url = IA_ITEM_PAGE.format(identifier=ident)
        webbrowser.open(url)

    def on_list_files(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        ident = self.results[idx].get("identifier")
        self.progress_label.config(text="Fetching metadata for {}".format(ident))
        self.fetch_files_btn.config(state=tk.DISABLED)
        t = threading.Thread(target=self._background_fetch_files, args=(ident,))
        t.daemon = True
        t.start()

    def _background_fetch_files(self, identifier):
        try:
            meta = get_item_metadata(identifier)
            files = meta.get("files", []) or []
            candidates = []
            for f in files:
                name = f.get("name")
                if not name:
                    continue
                lower = name.lower()
                if any(lower.endswith(suf) for suf in CANDIDATE_SUFFIXES):
                    candidates.append(name)
            # Fallback: include all files if none matched
            if not candidates:
                candidates = [f.get("name") for f in files if f.get("name")]
            self.queue.put((self._on_files_ready, (identifier, candidates)))
        except Exception as e:
            self.queue.put((self._on_files_error, (identifier, e)))

    def _on_files_ready(self, identifier, candidates):
        self.files_combo['values'] = candidates
        if candidates:
            self.files_combo.current(0)
            self.download_btn.config(state=tk.NORMAL)
            self.progress_label.config(text="{} candidate files found".format(len(candidates)))
        else:
            self.progress_label.config(text="No files found in metadata")
            self.download_btn.config(state=tk.DISABLED)
        self.fetch_files_btn.config(state=tk.NORMAL)

    def _on_files_error(self, identifier, err):
        messagebox.showerror("Metadata failed", "Failed to fetch metadata for {}\n{}".format(identifier, err))
        self.progress_label.config(text="Metadata error")
        self.fetch_files_btn.config(state=tk.NORMAL)

    def on_download(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        ident = self.results[idx].get("identifier")
        filename = self.files_combo.get()
        if not filename:
            messagebox.showinfo("Select file", "Please select a file from the candidate list.")
            return
        target_dir = filedialog.askdirectory(title="Select download folder")
        if not target_dir:
            return
        self.download_btn.config(state=tk.DISABLED)
        self.progress_label.config(text="Starting download...")
        t = threading.Thread(target=self._background_download, args=(ident, filename, target_dir))
        t.daemon = True
        t.start()

    def _background_download(self, ident, filename, target_dir):
        try:
            def progress_cb(done, total):
                if total:
                    pct = int(done * 100 / total)
                    self.queue.put((self._update_progress, (u"Downloading {} — {}%".format(filename, pct),)))
                else:
                    self.queue.put((self._update_progress, (u"Downloaded {} bytes".format(done),)))
            dest = download_file(ident, filename, target_dir, progress_callback=progress_cb)
            self.queue.put((self._on_download_complete, (dest,)))
        except Exception as e:
            self.queue.put((self._on_download_error, (e,)))

    def _update_progress(self, text):
        self.progress_label.config(text=text)

    def _on_download_complete(self, path):
        messagebox.showinfo("Download complete", "Saved to: {}".format(path))
        self.progress_label.config(text="Download finished")
        self.download_btn.config(state=tk.NORMAL)

    def _on_download_error(self, err):
        messagebox.showerror("Download failed", str(err))
        self.progress_label.config(text="Download failed")
        self.download_btn.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    # On older Windows, default fonts may be tiny; set a minimal geometry
    try:
        root.geometry("800x600")
    except Exception:
        pass
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()