from pathlib import Path
from app.config import OUTPUT_DIR, ROOT_DIR


def file_url(path: str | Path) -> str | None:
    p = Path(path)
    try:
        p = p.resolve()
        rel = p.relative_to(OUTPUT_DIR.resolve())
        return "/files/" + rel.as_posix()
    except Exception:
        return None


def enrich_output_urls(result):
    """Adiciona *_url recursivamente para paths de outputs."""
    if isinstance(result, dict):
        out = {}
        for k, v in result.items():
            out[k] = enrich_output_urls(v)
            if isinstance(v, str) and (k.endswith("_path") or k in {"classification_path", "preview_path", "raster_path"}):
                url = file_url(v)
                if url:
                    out[k.removesuffix("_path") + "_url"] = url
        return out
    if isinstance(result, list):
        return [enrich_output_urls(x) for x in result]
    return result
