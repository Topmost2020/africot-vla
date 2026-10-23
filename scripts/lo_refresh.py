"""Refresh fields and export PDF with LibreOffice (UNO). Run with LibreOffice's own python:

    <LO>/program/python.exe scripts/lo_refresh.py in.docx [--keep-docx]

Starts a headless soffice, updates all indexes (TOC, list of figures, list of tables) twice, writes <in>.pdf and,
unless --no-docx, saves the refreshed document back to <in>.docx (so the TOC fields carry cached entries).
Environment: LO_PROGRAM must point to the LibreOffice program directory.
"""
import os, sys, time, subprocess
sys.path.insert(0, os.environ["LO_PROGRAM"])
import uno
from com.sun.star.beans import PropertyValue


def pv(n, v):
    p = PropertyValue()
    p.Name, p.Value = n, v
    return p


def main(path, save_docx=True):
    prog = os.environ["LO_PROGRAM"]
    port = 2002
    proc = subprocess.Popen([os.path.join(prog, "soffice.exe"), "--headless", "--invisible", "--norestore", "--nologo",
                             f"--accept=socket,host=localhost,port={port};urp;", "-env:UserInstallation=file:///" + os.environ.get("LO_PROFILE", "C:/lo_profile")])
    ctx = None
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(60):
        try:
            ctx = resolver.resolve(f"uno:socket,host=localhost,port={port};urp;StarOffice.ComponentContext")
            break
        except Exception:
            time.sleep(1)
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    url = uno.systemPathToFileUrl(os.path.abspath(path))
    doc = desktop.loadComponentFromURL(url, "_blank", 0, (pv("Hidden", True),))
    for _ in range(2):
        idx = doc.getDocumentIndexes()
        for i in range(idx.getCount()):
            idx.getByIndex(i).update()
        doc.getTextFields().refresh()
        doc.refresh()
    pdf = os.path.splitext(os.path.abspath(path))[0] + ".pdf"
    doc.storeToURL(uno.systemPathToFileUrl(pdf), (pv("FilterName", "writer_pdf_Export"),))
    if save_docx:
        doc.storeToURL(url, (pv("FilterName", "MS Word 2007 XML"),))
    doc.close(True)
    try:
        desktop.terminate()
    except Exception:
        pass
    proc.wait(timeout=60)
    print("done", pdf)


if __name__ == "__main__":
    main(sys.argv[1], "--no-docx" not in sys.argv)
