"""Build a minimal synthetic parser fixture; no personal Word document is needed."""

import sys
import zipfile
from pathlib import Path

XML = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Synthetic rules</w:t></w:r></w:p>
<w:p><w:r><w:t>RULE: Review changes before applying them.</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/></w:numPr></w:pPr><w:r><w:t>Keep backups local.</w:t></w:r></w:p>
</w:body></w:document>"""

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("synthetic.docx")
    if target.exists():
        raise SystemExit("Refusing to replace existing file")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", XML)
    print(target)
