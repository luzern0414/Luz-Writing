"""Load the shared Crawl evidence gate without creating a project (numbered package helper)."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path

# ---- project-mode expiry waiver (the same text in Luz-Ops, Luz-System, Luz-Dev and Luz-Writing; a test compares the four copies) ----
EXPIRY_MARK = "检索记录超过七天"  # Luz-Crawl's validator ends every record older than seven days with this sentence; do not reword it


def project_scripts():
    """Luz-Project's scripts folder: ``LUZ_PROJECT_SCRIPTS`` (tests, rehearsals) or the sibling skill."""
    return Path(os.environ.get("LUZ_PROJECT_SCRIPTS") or Path(__file__).resolve().parents[2] / "Luz-Project" / "scripts")


def expiry_waived(project, stage):
    """Project mode: does Luz-Project judge ``stage`` complete (files approved by the user, client input and action gates through)? Then its Crawl record
    only has to exist, be valid and be concluded. The one judgement is ``approval_docs.crawl_expiry_waived`` (Luz-Project references/runbook.md, section 12);
    its folder is appended to sys.path, so this skill's own modules win on a name clash. Without a stage, without Luz-Project or when it cannot answer: False."""
    if not stage:
        return False
    import sys
    folder = project_scripts()
    if not (folder / "approval_docs.py").is_file():
        return False
    saved = list(sys.path)
    try:
        if str(folder) not in sys.path:
            sys.path.append(str(folder))
        import approval_docs  # type: ignore[import-not-found]
        return bool(approval_docs.crawl_expiry_waived(project, stage))
    except Exception:  # noqa: BLE001 - any failure to ask means the age counts
        return False
    finally:
        sys.path[:] = saved


def drop_expired(errors, project, stage):
    """Only the seven-day finding leaves ``errors``, and only when Luz-Project waives it for ``stage``; every other finding stays."""
    if not any(EXPIRY_MARK in str(e) for e in errors) or not expiry_waived(project, stage):
        return errors
    return [e for e in errors if EXPIRY_MARK not in str(e)]
# ---- end of project-mode expiry waiver ----

def crawl_errors(session, stage=None, caller=None, state_root=None):
    """Luz-Crawl's check of the preflight record of ``stage`` in ``session``. In project mode (``stage`` is a Luz-Project stage) the seven-day finding is dropped when
    Luz-Project judges the stage complete; ``state_root`` names the project when ``session`` is a skill session that is not itself the project."""
    root = Path(os.environ.get("LUZ_CRAWL_ROOT") or Path(__file__).resolve().parents[2] / "Luz-Crawl")
    source = root / "scripts" / "crawl_preflight.py"
    if not source.is_file():
        return [f"Crawl 前置检索校验器不存在: {source}"]
    spec = importlib.util.spec_from_file_location("_luz_crawl_preflight", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if stage is None:
        stage = os.environ.get("LUZ_CRAWL_STAGE") or None
    caller = caller or Path(__file__).resolve().parents[1].name.lower()
    owner = module.stage_evidence_caller(session, caller, stage) if hasattr(module, "stage_evidence_caller") else caller
    errors = module.validate_preflight(Path(session), owner, stage)
    # Standalone stages now also have explicit names. A name alone must not
    # make a standalone session ask the project's expiry-waiver interface.
    project = Path(state_root or session)
    return drop_expired(errors, state_root or session, stage) if (project / "project.json").is_file() else errors
