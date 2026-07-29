# Clinic Water Networks

This folder is self-contained. It includes the complete and 13-neighborhood
clinic environments, water-source data, coverage data, and Porto Alegre
neighborhood boundaries converted from `bairros_vigentes`.

Because browsers block local `fetch()` requests from `file://` pages, start a
small static server inside this folder:

```powershell
python -m http.server 8765
```

Then open <http://localhost:8765/>.

The folder can be moved outside the LODUS repository without changing any
paths or copying additional files.
