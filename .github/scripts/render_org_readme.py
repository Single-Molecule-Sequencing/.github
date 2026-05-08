#!/usr/bin/env python3
"""Generate and publish the Single-Molecule-Sequencing org profile README.

Reads the live org repo list via `gh api`, categorizes repos, verifies link
health, renders a markdown landing page, and publishes idempotently to
`Single-Molecule-Sequencing/.github/profile/README.md`.

See SKILL.md for full documentation.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

ORG = "Single-Molecule-Sequencing"
PROFILE_REPO = ".github"
PROFILE_REPO_PRIVATE = ".github-private"
PROFILE_PATH = "profile/README.md"
CACHE_DIR = Path.home() / ".cache" / "org-readme"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Repo categorization

# Repos that form the core lab infrastructure stack.
INFRA_REPOS = {
    "ont-ecosystem",
    "lab-system",
    "lab-papers",
    "lab-wiki",
    "lab-experiments",
    "lab-context",
    "lab-agent",
    "SMS_infrastructure",
    "ont-registry",
    "seq-registry",
    "lab-onboarding",
    "dev-env-setup",
}

# Active project coordination shells (the .project/ pattern).
PROJECT_REPOS = {
    "golden-gate",
    "golden-gate-methods",
    "cas9-targeted-sequencing",
    "telomere-sequencing",
    "adaptive-sampling",
    "smaseq",
    "fine-tuning",
    "lab-math",
    "single-read-single-cell-diplotyping",
    "programmable-nuclease-activity",
    "pharmvar-pangenome-pipeline",
    "CYP2D7-Level2-Plasmid-Analysis",
    "longevity-platform-grant",
    "longevity-epigenetics",
    "pacbio-cas9-walkthrough",
}

# Wet-lab and analysis tooling — single-purpose utility repos.
TOOLING_REPOS = {
    "dorado-run",
    "dorado-bench",
    "dorado-bench-interactive",
    "barbell",
    "sss",
    "fragment-viewer",
    "Reference_Fasta_Generator",
    "PGx-prep",
    "CypScope",
    "CypScope-prep",
    "ONT-SMA-seq",
    "ONT_raw_data_explorer",
    "End_reason_tagger",
    "End_Reason_nf",
    "sma-seq-workspace",
    "smaseq-qc",
    "sms-pipeline",
    "SMA_Seq_Figures",
}

# Lab websites and documentation sites.
SITE_REPOS = {
    "single-molecule-sequencing.github.io",
    "AtheyLab-Website",
    "sms-textbook-web",
    "runge-website",
    "portal",
    "demo-repository",
}

# Public-facing dashboards and Pages (homepageUrl that should appear up top).
FEATURED_DASHBOARDS = [
    {
        "name": "🌐 Athey Lab Website",
        "url": "https://atheylab.org",
        "fallback": "https://single-molecule-sequencing.github.io/AtheyLab-Website/",
        "blurb": "Public-facing lab homepage: people, publications, news.",
    },
    {
        "name": "📚 SMS Textbook (Web Edition)",
        "url": "https://single-molecule-sequencing.github.io/sms-textbook-web/",
        "blurb": "8-volume Quarto book on Single-Molecule Sequencing for Pharmacogenomics — 349 chapters, fully searchable.",
    },
    {
        "name": "🧬 ont-ecosystem Docs",
        "url": "https://single-molecule-sequencing.github.io/ont-ecosystem/",
        "blurb": "Skill catalog and CLI reference for the lab's primary analysis framework (153 lib modules, 80+ skills).",
    },
    {
        "name": "🧪 Sample-Sheet Generator",
        "url": "https://single-molecule-sequencing.github.io/sss/",
        "blurb": "Browser-based wet-lab sample-sheet builder for ONT runs.",
    },
    {
        "name": "🏠 Org Landing",
        "url": "https://single-molecule-sequencing.github.io/",
        "blurb": "Org-level Pages site with live pulse, paper portfolio, and project knowledge graph.",
    },
]

# Manual hints for repos with thin descriptions.
DESCRIPTION_OVERRIDES: dict[str, str] = {
    ".github": "Org profile repository (this README).",
    ".github-private": "Private org profile assets.",
    "single-molecule-sequencing.github.io": "Org-level GitHub Pages site (Jekyll).",
    "EndReason": "Notebooks: end-reason analysis exploration.",
    "Error-Rate-SMS": "Notebooks: error-rate determination from sequence-defined standards.",
    "SMS": "Lab notebooks: cross-cutting SMS exploration.",
    "Textbook": "Early SMS textbook prototype (archived).",
    "demo-repository": "GitHub-provided demo repo template.",
    "spec-kit": "💫 Toolkit for Spec-Driven Development (vendored).",
    "_lab-render-canary": "CI canary repo for lab-papers reusable workflows.",
    "_smoke-lab-paper-template-24978290870": "Auto-spawned smoke-test repo (will be deleted by template-smoke workflow).",
    "End_reason_tagger": "Shell pipeline that tags ONT reads with their end_reason metadata.",
    "ONT_raw_data_explorer": "Notebook-driven explorer for raw ONT POD5/FAST5 data.",
    "End_Reason_nf": "Nextflow pipeline implementing the end-reason QC workflow.",
    "golden-gate-methods": "Type-IIS Golden Gate cloning methods paper (companion to /golden-gate-assembly skill).",
    "paper-proficiency-testing-plasmids": "Plasmid-standard proficiency-testing paper (CYP2D6 standards for SMA-seq calibration).",
    "paper-plasmid-standards-proof": "Empirical proof that plasmid standards anchor SMA-seq error-rate calibration.",
    "paper-cyp2d6-breast-cancer-targeted": "CYP2D6 targeted long-read sequencing in breast-cancer pharmacogenomics.",
    "paper-bsl2-targeted-long-read": "Long-read targeted sequencing protocol for BSL2-class clinical samples.",
    "Wolfe_Thesis_final": "Monica J. Wolfe PhD dissertation (final version) — single-molecule long-read sequencing for complex loci.",
    "lab-context": "Earlier ambient-context experiment, partially superseded by lab-system. Pending reconciliation.",
    "SMA_seq_test": "Lightweight SMA-seq integration tests.",
    "pharmvar-pangenome-pipeline": "Pangenome-aware variant resolution against the PharmVar haplotype set.",
}

# Force-classify these into specific categories regardless of name patterns.
CATEGORY_OVERRIDES: dict[str, str] = {
    "cas9-clc-ce-methods": "paper",
    "golden-gate-methods": "paper",
    "EndReason": "tooling",
    "SMS": "tooling",
    "Error-Rate-SMS": "tooling",
    "SMA_seq_test": "tooling",
    "demo-repository": "scratch",
}

# Repos to drop entirely from the README listing.
# - .github and .github-private are this skill's own publish targets; including
#   them creates a feedback loop (each publish bumps their pushedAt, which
#   reshuffles the table on the next render).
SKIP_REPOS: set[str] = {".github", ".github-private"}


@dataclass
class Repo:
    name: str
    description: str
    homepage: str
    pushed_at: str
    visibility: str
    archived: bool
    primary_language: str | None
    stargazer_count: int

    @property
    def url(self) -> str:
        return f"https://github.com/Single-Molecule-Sequencing/{self.name}"

    @property
    def display_description(self) -> str:
        if self.name in DESCRIPTION_OVERRIDES:
            return DESCRIPTION_OVERRIDES[self.name]
        return self.description.strip() or "_(no description)_"

    @property
    def visibility_badge(self) -> str:
        return {
            "PUBLIC": "🌍 public",
            "PRIVATE": "🔒 private",
            "INTERNAL": "🏛️ internal",
        }.get(self.visibility, self.visibility.lower())

    @property
    def language_badge(self) -> str:
        if not self.primary_language:
            return ""
        return f"`{self.primary_language}`"

    @property
    def freshness_emoji(self) -> str:
        days = self._days_since_push()
        if days < 7:
            return "🟢"  # active this week
        if days < 30:
            return "🟡"  # active this month
        if days < 180:
            return "🟠"  # quiet
        return "⚪"  # cold

    def _days_since_push(self) -> int:
        if not self.pushed_at:
            return 9999
        try:
            dt = datetime.fromisoformat(self.pushed_at.replace("Z", "+00:00"))
        except ValueError:
            return 9999
        return (datetime.now(tz=timezone.utc) - dt).days

    @property
    def category(self) -> str:
        if self.archived:
            return "archived"
        n = self.name
        if n in CATEGORY_OVERRIDES:
            return CATEGORY_OVERRIDES[n]
        if n in SITE_REPOS:
            return "site"
        if n in INFRA_REPOS:
            return "infra"
        if n in PROJECT_REPOS:
            return "project"
        if n in TOOLING_REPOS:
            return "tooling"
        if n.endswith("-template") or n.startswith("lab-paper-template"):
            return "template"
        if n.startswith("paper-") or n in {"SMAseq_paper", "Wolfe_Thesis_final", "Wolfe_Thesis", "monica_thesis", "sg-ncc2003-manuscript", "end-reason-paper", "endreason_manuscript", "End_Reason_Manuscript", "paper-end-reason"}:
            return "paper"
        if n.startswith("_smoke-") or n.startswith("_") or n in {"demo-repository", "spec-kit"}:
            return "scratch"
        return "other"


# ---------------------------------------------------------------------------
# GitHub helpers

def gh_api(path: str, method: str = "GET", payload: dict | None = None) -> Any:
    """Run `gh api <path>` and return parsed JSON."""
    cmd = ["gh", "api", "--method", method, path]
    if payload is not None:
        cmd.extend(["--input", "-"])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=json.dumps(payload) if payload else None,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh api {path} failed: {proc.stderr}")
    out = proc.stdout.strip()
    if not out:
        return None
    return json.loads(out)


def fetch_repos() -> list[Repo]:
    """Fetch all org repos with the metadata we need."""
    cmd = [
        "gh", "repo", "list", ORG, "--limit", "200",
        "--json",
        "name,description,visibility,isArchived,homepageUrl,pushedAt,stargazerCount,primaryLanguage",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    raw = json.loads(proc.stdout)
    repos: list[Repo] = []
    for r in raw:
        if r["name"] in SKIP_REPOS:
            continue
        repos.append(Repo(
            name=r["name"],
            description=r.get("description") or "",
            homepage=(r.get("homepageUrl") or "").strip(),
            pushed_at=r.get("pushedAt", ""),
            visibility=r.get("visibility", "PRIVATE"),
            archived=r.get("isArchived", False),
            primary_language=(r.get("primaryLanguage") or {}).get("name"),
            stargazer_count=r.get("stargazerCount", 0),
        ))
    return repos


# ---------------------------------------------------------------------------
# Link health

def head(url: str, timeout: int = 6) -> int:
    """Return HTTP status code for a HEAD request, or 0 on network error."""
    try:
        req = urllib_request.Request(url, method="HEAD", headers={"User-Agent": "org-readme/1.0"})
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib_error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def verify_links(urls: list[str]) -> dict[str, int]:
    """HEAD every URL in parallel; return {url: status_code}."""
    results: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(head, u): u for u in urls}
        for f in as_completed(futs):
            results[futs[f]] = f.result()
    return results


# ---------------------------------------------------------------------------
# Rendering

def fmt_repo_row(r: Repo) -> str:
    """Single markdown table row for a repo."""
    bits = [r.visibility_badge]
    if r.language_badge:
        bits.append(r.language_badge)
    badge = " · ".join(bits)
    homepage_link = ""
    if r.homepage and r.homepage.startswith("http"):
        homepage_link = f" · [🔗 site]({r.homepage})"
    return (
        f"| {r.freshness_emoji} [`{r.name}`]({r.url}){homepage_link} "
        f"| {r.display_description} "
        f"| {badge} |"
    )


def fmt_repo_table(repos: list[Repo], heading: str, blurb: str = "") -> str:
    if not repos:
        return ""
    lines = [f"### {heading}"]
    if blurb:
        lines.append("")
        lines.append(blurb)
    lines.append("")
    lines.append("| Repo | Description | Meta |")
    lines.append("|---|---|---|")
    for r in sorted(repos, key=lambda x: x.pushed_at, reverse=True):
        lines.append(fmt_repo_row(r))
    lines.append("")
    return "\n".join(lines)


def fmt_dashboards(verified: dict[str, int]) -> str:
    lines = ["## 🚀 Quick links — dashboards & live sites", ""]
    for d in FEATURED_DASHBOARDS:
        url = d["url"]
        status = verified.get(url, 0)
        if status >= 400 or status == 0:
            url = d.get("fallback", url)
            status = verified.get(url, 0)
        if status >= 400 or status == 0:
            continue  # silently drop fully broken entries
        lines.append(f"- **[{d['name']}]({url})** — {d['blurb']}")
    lines.append("")
    return "\n".join(lines)


def fmt_infra_diagram() -> str:
    return """## 🏗️ Lab infrastructure stack

```mermaid
flowchart TB
    subgraph Layer4["📚 Layer 4 — Publication"]
        L4A["lab-papers<br/>(paper repos, atom system,<br/>variants/CI)"]
        L4B["lab-wiki<br/>(decisions, transcripts,<br/>knowledge base)"]
        L4C["lab-paper-template<br/>lab-project-template"]
    end
    subgraph Layer3["🧪 Layer 3 — Analysis"]
        L3A["ont-ecosystem<br/>(80+ skills, 150+ libs,<br/>30+ CLI tools)"]
        L3B["smaseq-qc<br/>(SMA-seq pipeline)"]
        L3C["dorado-run, barbell, PGx-prep<br/>(specialized tooling)"]
    end
    subgraph Layer2["📊 Layer 2 — Registry"]
        L2A["lab-experiments<br/>(unified ONT+PacBio+Illumina)"]
        L2B["ont-registry<br/>(active ONT registry)"]
        L2C["seq-registry<br/>(oligos, duplexes)"]
    end
    subgraph Layer1["💾 Layer 1 — Data"]
        L1A["Raw POD5/BAM/FASTQ<br/>(local + Great Lakes HPC)"]
        L1B["Reference genomes<br/>(GRCh38 primary-only)"]
    end
    Layer1 --> Layer2 --> Layer3 --> Layer4
    L3A -. orchestrates .-> L2B
    L4A -. cites .-> L4B
```

The four-tier stack lets every paper trace its claims back to raw reads
through a registry and a reproducible analysis pipeline.
"""


def fmt_header(stats: dict) -> str:
    return f"""<div align="center">

# Single Molecule Sequencing

**Long-read genomics, pharmacogenomics, and methods development at the [Athey Lab](https://atheylab.org), University of Michigan**

[![Athey Lab](https://img.shields.io/badge/Athey%20Lab-University%20of%20Michigan-00274C?style=flat-square)](https://atheylab.org)
[![Repos](https://img.shields.io/badge/repos-{stats['total']}-blue?style=flat-square)](https://github.com/orgs/Single-Molecule-Sequencing/repositories)
[![Public](https://img.shields.io/badge/public-{stats['public']}-success?style=flat-square)](https://github.com/orgs/Single-Molecule-Sequencing/repositories?q=visibility%3Apublic)
[![Updated](https://img.shields.io/badge/profile-auto--updated%20daily-brightgreen?style=flat-square)](https://github.com/Single-Molecule-Sequencing/.github/blob/master/.github/workflows/update-org-readme.yml)

</div>

---

## 🔬 What we do

We build **single-molecule, long-read sequencing methods** — Oxford Nanopore Technologies (ONT) and PacBio HiFi — to attack genomic problems that short-read sequencing cannot solve cleanly: structural variation in pharmacogenes (CYP2D6 / CYP2D7 / CYP2D8P), ssDNA size distribution at single-base resolution, repeat expansions, methylation aging clocks, and Cas9-targeted enrichment QC.

Our codebase is organized as a **four-tier infrastructure stack** (data → registry → analysis → publication) that lets every published claim trace back to raw reads through a versioned, reproducible pipeline. The org hosts {stats['total']} repositories ({stats['public']} public · {stats['private']} private · {stats['archived']} archived) covering ~{stats['active_papers']} active manuscripts, ~{stats['active_projects']} project shells, and the analysis frameworks they share.

"""


def fmt_legend() -> str:
    return """<details>
<summary>🧭 Marker legend</summary>

| Marker | Meaning |
|---|---|
| 🟢 | Active this week |
| 🟡 | Active this month |
| 🟠 | Active in the last 6 months |
| ⚪ | Quiet (>6 months) |
| 🌍 public | Open to the world |
| 🔒 private | Members of `Single-Molecule-Sequencing` only |
| 🏛️ internal | UM enterprise-internal |
| 🔗 site | Has a live GitHub Pages or external homepage |

</details>

"""


def render(repos: list[Repo], verified: dict[str, int], render_ts: datetime) -> str:
    by_cat: dict[str, list[Repo]] = {}
    for r in repos:
        by_cat.setdefault(r.category, []).append(r)

    stats = {
        "total": len(repos),
        "public": sum(1 for r in repos if r.visibility == "PUBLIC"),
        "private": sum(1 for r in repos if r.visibility == "PRIVATE"),
        "internal": sum(1 for r in repos if r.visibility == "INTERNAL"),
        "archived": sum(1 for r in repos if r.archived),
        "active_papers": sum(1 for r in repos if r.category == "paper"),
        "active_projects": sum(1 for r in repos if r.category == "project"),
    }

    parts: list[str] = []
    parts.append(fmt_header(stats))
    parts.append(fmt_dashboards(verified))
    parts.append(fmt_infra_diagram())
    parts.append("\n## 📦 Repositories\n")
    parts.append("Every active and archived repo in the org, grouped by purpose. Stamps reflect last `git push` time.\n")
    parts.append(fmt_legend())

    parts.append(fmt_repo_table(
        by_cat.get("infra", []),
        "🏗️ Core infrastructure",
        "The substrate everything else depends on — registries, analysis frameworks, paper-build tooling, ambient lab-context runtime.",
    ))
    parts.append(fmt_repo_table(
        by_cat.get("paper", []),
        "📝 Manuscripts in progress",
        "One repo per paper. Each follows the lab atom-system convention (variants/, atoms/, content/, CI auto-builds PDFs on push).",
    ))
    parts.append(fmt_repo_table(
        by_cat.get("project", []),
        "🧪 Active project workspaces",
        "Project-coordination shells (`.project/` + `CLAUDE.md` pattern). Each wraps wet-lab + dry-lab work toward a single research question.",
    ))
    parts.append(fmt_repo_table(
        by_cat.get("tooling", []),
        "🔧 Wet-lab and analysis tooling",
        "Specialized utilities — basecallers, demultiplexers, sample-sheet generators, reference builders, fragment viewers.",
    ))
    parts.append(fmt_repo_table(
        by_cat.get("site", []),
        "🌐 Websites and documentation",
        "Public-facing landing pages and documentation sites built with Jekyll, Quarto, or static HTML.",
    ))
    parts.append(fmt_repo_table(
        by_cat.get("template", []),
        "🧬 Repo templates",
        "Spawn a new lab repo with `gh repo create <new> --template Single-Molecule-Sequencing/<template>`.",
    ))
    if by_cat.get("other"):
        parts.append(fmt_repo_table(by_cat["other"], "🗂️ Other", ""))

    if by_cat.get("archived"):
        parts.append("<details>\n<summary>📦 Archived repositories ({})</summary>\n\n".format(len(by_cat["archived"])))
        parts.append(fmt_repo_table(by_cat["archived"], "Archived", "Preserved for git history; superseded by newer canonical repos."))
        parts.append("</details>\n")

    if by_cat.get("scratch"):
        parts.append("<details>\n<summary>🧹 Scratch / vendored / smoke-test ({})</summary>\n\n".format(len(by_cat["scratch"])))
        parts.append(fmt_repo_table(by_cat["scratch"], "Scratch", "Auto-spawned smoke-test repos, vendored third-party tools, demo content."))
        parts.append("</details>\n")

    parts.append(fmt_footer(stats, render_ts, verified))
    return "\n".join(parts)


def fmt_footer(stats: dict, ts: datetime, verified: dict[str, int]) -> str:
    broken = [u for u, s in verified.items() if s >= 400 or s == 0]
    broken_note = ""
    if broken:
        broken_note = f"\n_Note: {len(broken)} link(s) flagged as unreachable in this run; they were dropped from Quick Links._\n"
    return f"""---

## 👥 People

The Single-Molecule-Sequencing org is the GitHub home of the **Athey Lab** at the University of Michigan, led by Brian D. Athey (PI). Active members include Greg Farnum, Monica Wolfe, Henry Li, Yisang Kim, Mingze Sun, Souma Mahapatra, Isaac Farnum, and Amber Walker. See the [Athey Lab People page](https://atheylab.org/people/) for the full roster.

## 📬 Contact

- **Lab email:** atheylab-sequencing@umich.edu
- **PI:** Brian D. Athey · bleu@umich.edu
- **Address:** Med Sci Building 1, 1301 Catherine St, Ann Arbor MI 48109
- **Bug reports / issues:** Open an issue in the relevant repo, or email the lab address above.

## 📊 Org stats

- **Total repositories:** {stats['total']}
- **Public:** {stats['public']} · **Private:** {stats['private']} · **Internal:** {stats['internal']} · **Archived:** {stats['archived']}
- **Active manuscripts:** {stats['active_papers']}
- **Active project workspaces:** {stats['active_projects']}

---

<sub>This page is auto-generated daily by the
[`/org-readme`](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/tree/main/skills/org-readme) skill
running in <a href="https://github.com/Single-Molecule-Sequencing/.github/blob/master/.github/workflows/update-org-readme.yml"><code>update-org-readme.yml</code></a>.
Last regenerated: <code>{ts.strftime("%Y-%m-%d")}</code>.{broken_note}</sub>
"""


# ---------------------------------------------------------------------------
# Publish

def publish_to(repo: str, content: str, *, force: bool = False, branch: str = "master") -> dict:
    """Push README content to <repo>/profile/README.md if content changed."""
    path = f"repos/Single-Molecule-Sequencing/{repo}/contents/{PROFILE_PATH}"
    existing_sha: str | None = None
    existing_b64: str | None = None
    try:
        existing = gh_api(path)
        existing_sha = existing["sha"]
        existing_b64 = existing["content"]
    except RuntimeError:
        pass

    new_b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    if existing_b64 and not force:
        try:
            if base64.b64decode(existing_b64).decode("utf-8") == content:
                return {"action": "skip", "repo": repo, "reason": "content matches", "sha": existing_sha}
        except Exception:
            pass

    payload: dict[str, Any] = {
        "message": f"chore(profile): auto-update org README ({datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')})",
        "content": new_b64,
        "branch": branch,
    }
    if existing_sha:
        payload["sha"] = existing_sha
    result = gh_api(path, method="PUT", payload=payload)
    return {"action": "publish", "repo": repo, "commit": result["commit"]["sha"][:7], "sha": result["content"]["sha"]}


def detect_default_branch(repo: str) -> str:
    """Probe the repo for its default branch (some repos use main, others master)."""
    try:
        meta = gh_api(f"repos/Single-Molecule-Sequencing/{repo}")
        return meta.get("default_branch", "master")
    except RuntimeError:
        return "master"


def publish(content: str, *, force: bool = False, also_private: bool = True) -> list[dict]:
    """Publish to .github (always) and .github-private (if requested)."""
    results: list[dict] = []
    branch_pub = detect_default_branch(PROFILE_REPO)
    results.append(publish_to(PROFILE_REPO, content, force=force, branch=branch_pub))
    if also_private:
        branch_priv = detect_default_branch(PROFILE_REPO_PRIVATE)
        results.append(publish_to(PROFILE_REPO_PRIVATE, content, force=force, branch=branch_priv))
    return results


def cleanup_desktop_ini() -> None:
    """The .github repo accidentally has desktop.ini files committed. Best-effort delete."""
    for repo_path in ("desktop.ini", "profile/desktop.ini"):
        path = f"repos/Single-Molecule-Sequencing/{PROFILE_REPO}/contents/{repo_path}"
        try:
            existing = gh_api(path)
            gh_api(path, method="DELETE", payload={
                "message": f"chore: remove stray {repo_path}",
                "sha": existing["sha"],
                "branch": "master",
            })
        except RuntimeError:
            pass


def upload_file(repo_path: str, content: str, commit_message: str) -> dict:
    """Upload (or update) a file in the .github repo at `repo_path`."""
    api_path = f"repos/Single-Molecule-Sequencing/{PROFILE_REPO}/contents/{repo_path}"
    existing_sha: str | None = None
    existing_b64: str | None = None
    try:
        existing = gh_api(api_path)
        existing_sha = existing["sha"]
        existing_b64 = existing["content"]
    except RuntimeError:
        pass
    if existing_b64:
        try:
            if base64.b64decode(existing_b64).decode("utf-8") == content:
                return {"action": "skip", "path": repo_path}
        except Exception:
            pass
    payload: dict[str, Any] = {
        "message": commit_message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": "master",
    }
    if existing_sha:
        payload["sha"] = existing_sha
    result = gh_api(api_path, method="PUT", payload=payload)
    return {"action": "upload", "path": repo_path, "commit": result["commit"]["sha"][:7]}


def install_workflow(skill_root: Path) -> list[dict]:
    """Vendor the render script and the workflow YAML into the .github repo.

    Daily cron lives in the .github repo, not in ont-ecosystem, so the workflow
    file must be pushed alongside a runnable copy of the script.
    """
    results: list[dict] = []

    script_src = skill_root / "scripts" / "render_org_readme.py"
    workflow_src = skill_root / "workflows" / "update-org-readme.yml"

    results.append(upload_file(
        ".github/scripts/render_org_readme.py",
        script_src.read_text(),
        "chore(workflow): vendor render_org_readme.py from ont-ecosystem",
    ))
    results.append(upload_file(
        ".github/workflows/update-org-readme.yml",
        workflow_src.read_text(),
        "chore(workflow): install daily org-readme cron",
    ))
    return results


# ---------------------------------------------------------------------------
# Main

def collect_urls_to_check(repos: list[Repo]) -> list[str]:
    urls: list[str] = []
    for d in FEATURED_DASHBOARDS:
        urls.append(d["url"])
        if "fallback" in d:
            urls.append(d["fallback"])
    for r in repos:
        if r.homepage and r.homepage.startswith("http"):
            urls.append(r.homepage)
    return list(dict.fromkeys(urls))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="Print rendered README to stdout; don't publish.")
    p.add_argument("--no-link-check", action="store_true", help="Skip HEAD requests on Pages URLs (faster).")
    p.add_argument("--force", action="store_true", help="Publish even when content matches existing.")
    p.add_argument("--output", type=Path, default=None, help="Also write rendered README to this path.")
    p.add_argument("--cleanup-desktop-ini", action="store_true", help="Remove the stray desktop.ini in the .github repo.")
    p.add_argument("--install-workflow", action="store_true", help="Vendor render_org_readme.py + update-org-readme.yml into the .github repo.")
    p.add_argument("--no-private", action="store_true", help="Only publish to .github (skip the .github-private member view).")
    p.add_argument("--only-private", action="store_true", help="Only publish to .github-private (skip the public .github view).")
    args = p.parse_args()

    t0 = time.time()
    print("[org-readme] fetching org repo list...", file=sys.stderr)
    repos = fetch_repos()
    print(f"[org-readme] {len(repos)} repos found", file=sys.stderr)

    verified: dict[str, int] = {}
    if not args.no_link_check:
        urls = collect_urls_to_check(repos)
        print(f"[org-readme] HEAD-checking {len(urls)} URLs...", file=sys.stderr)
        verified = verify_links(urls)
        broken = [u for u, s in verified.items() if s == 0 or s >= 400]
        if broken:
            print(f"[org-readme] {len(broken)} broken: {broken[:5]}{'...' if len(broken) > 5 else ''}", file=sys.stderr)

    rendered = render(repos, verified, datetime.now(tz=timezone.utc))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
        print(f"[org-readme] wrote {args.output}", file=sys.stderr)

    cache_path = CACHE_DIR / "last-rendered.md"
    cache_path.write_text(rendered)

    log = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "repos_seen": len(repos),
        "links_checked": len(verified),
        "broken_links": [u for u, s in verified.items() if s == 0 or s >= 400],
        "elapsed_sec": round(time.time() - t0, 2),
        "sha256_of_rendered": hashlib.sha256(rendered.encode()).hexdigest()[:16],
    }

    if args.dry_run:
        print(rendered)
        log["action"] = "dry-run"
    else:
        if args.cleanup_desktop_ini:
            cleanup_desktop_ini()
        if args.install_workflow:
            skill_root = Path(__file__).resolve().parents[1]
            install_results = install_workflow(skill_root)
            for r in install_results:
                print(f"[org-readme] workflow-install: {r['action']} {r['path']}", file=sys.stderr)
            log["workflow_install"] = install_results
        if args.only_private:
            results = [publish_to(PROFILE_REPO_PRIVATE, rendered, force=args.force,
                                  branch=detect_default_branch(PROFILE_REPO_PRIVATE))]
        else:
            results = publish(rendered, force=args.force, also_private=not args.no_private)
        log["publishes"] = results
        for r in results:
            tag = f"{r['repo']}: {r['action']}"
            if r["action"] == "publish":
                tag += f" → {r.get('commit', '?')}"
            print(f"[org-readme] {tag}", file=sys.stderr)

    (CACHE_DIR / "last-run.json").write_text(json.dumps(log, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
