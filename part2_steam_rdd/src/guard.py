"""Check that the analysis plan is committed before estimating effects."""
from __future__ import annotations

import subprocess
from pathlib import Path


def plan_is_committed(plan: Path) -> tuple[bool, str]:
    try:
        cwd = str(plan.parent)
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", plan.name],
                                 cwd=cwd, capture_output=True, text=True)
        if tracked.returncode != 0:
            return False, f"{plan.name} is not committed to git yet."
        dirty = subprocess.run(["git", "status", "--porcelain", plan.name],
                               cwd=cwd, capture_output=True, text=True)
        if dirty.stdout.strip():
            return False, f"{plan.name} has uncommitted changes."
        last = subprocess.run(["git", "log", "-1", "--format=%h %ci", "--", plan.name],
                              cwd=cwd, capture_output=True, text=True)
        return True, f"Plan committed in {last.stdout.strip()}"
    except FileNotFoundError:
        return False, "git is not installed or not in PATH."
