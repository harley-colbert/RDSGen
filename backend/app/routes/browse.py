from concurrent.futures import ProcessPoolExecutor
from flask import request, jsonify
from .blueprint import api_bp

# TK worker must be top-level (Windows spawn pickles the callable)
def _tk_browse_worker(mode: str, title: str, initial: str | None, filters: str) -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()

    # Convert "Label|*.ext;Label2|*.ext2" → tkinter filetypes list
    filetypes = []
    if filters:
        for part in filters.split(";"):
            if "|" in part:
                lbl, pat = part.split("|", 1)
                filetypes.append((lbl.strip(), pat.strip()))

    if mode == "open_dir":
        path = filedialog.askdirectory(title=title, initialdir=initial or None) or ""
    elif mode == "save_file":
        path = filedialog.asksaveasfilename(
            title=title, initialdir=initial or None,
            filetypes=filetypes or [("All files", "*.*")]
        ) or ""
    else:  # open_file
        path = filedialog.askopenfilename(
            title=title, initialdir=initial or None,
            filetypes=filetypes or [("All files", "*.*")]
        ) or ""

    try:
        root.destroy()
    except Exception:
        pass
    return path

@api_bp.get("/browse")
def browse_dialog():
    """Open a native Windows dialog using tkinter.filedialog in a separate process."""
    mode = request.args.get("mode", "open_file")
    title = request.args.get("title", "") or "Select a file"
    initial = request.args.get("initial", "") or None
    filters = request.args.get("filters", "")

    try:
        with ProcessPoolExecutor(max_workers=1) as ex:
            path = ex.submit(_tk_browse_worker, mode, title, initial, filters).result()
        return jsonify({"ok": True, "path": path}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
