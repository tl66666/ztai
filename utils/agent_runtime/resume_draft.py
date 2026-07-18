from __future__ import annotations

from dataclasses import dataclass
import re


SECTION_HEADINGS = {
    "基本信息", "教育经历", "工作经历", "实习经历", "项目经历", "专业技能",
    "技能", "获奖经历", "证书", "自我评价",
}
_BULLET_PREFIX = re.compile(r"^\s*[•●▪◦·—–]\s*")
_SPACE = re.compile(r"[ \t]+")


@dataclass(frozen=True)
class ResumeDraft:
    content: str
    mode: str
    changes: tuple[str, ...]


def local_resume_draft(content: str, target_role: str = "") -> ResumeDraft:
    """Create a source-faithful local draft without inventing achievements."""
    original = str(content or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = original.split("\n")
    cleaned: list[str] = []
    changes: list[str] = []
    blank_pending = False

    for raw_line in lines:
        line = _SPACE.sub(" ", raw_line).strip()
        if not line:
            if cleaned:
                blank_pending = True
            continue
        if blank_pending:
            cleaned.append("")
            blank_pending = False
        normalized = _BULLET_PREFIX.sub("- ", line)
        if normalized != line:
            changes.append("统一了项目要点的项目符号")
        heading = normalized.rstrip("：:").strip()
        if heading in SECTION_HEADINGS and normalized != heading:
            normalized = heading
            changes.append("统一了简历章节标题格式")
        cleaned.append(normalized)

    draft = "\n".join(cleaned).strip()
    target = str(target_role or "").strip()
    if target and "求职目标" not in draft and "目标岗位" not in draft:
        draft = f"求职目标：{target}\n\n{draft}" if draft else f"求职目标：{target}"
        changes.append("补充了已确认的求职目标")
    if not changes:
        changes.append("保留原始事实，仅规范了排版")
    return ResumeDraft(draft, "local", tuple(dict.fromkeys(changes)))


def local_resume_diagnosis(content: str, target_role: str = "") -> str:
    """Return an evidence-based diagnosis that remains useful without a model key."""
    text = str(content or "").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    headings = {line.rstrip("：:") for line in lines if line.rstrip("：:") in SECTION_HEADINGS}
    bullet_count = sum(1 for line in lines if _BULLET_PREFIX.match(line) or line.startswith("- "))
    quantified = len(re.findall(r"\d+(?:%|个|次|项|人|天|万|k|K)", text))
    issues: list[str] = []
    if "项目经历" not in headings and "工作经历" not in headings and "实习经历" not in headings:
        issues.append("缺少清晰的项目、工作或实习经历章节")
    if not ("技能" in headings or "专业技能" in headings):
        issues.append("缺少独立的技能章节，HR 难以快速定位技术栈")
    if bullet_count < 3:
        issues.append("项目要点较少，建议把职责拆成可扫描的动作要点")
    if quantified == 0:
        issues.append("缺少量化或可验证结果，建议补充规模、效率、质量或产出证据")
    if target_role and target_role.lower() not in text.lower():
        issues.append(f"尚未显式对齐目标岗位“{target_role}”")
    strengths: list[str] = []
    if headings:
        strengths.append(f"已识别 {len(headings)} 个结构章节")
    if bullet_count:
        strengths.append(f"已有 {bullet_count} 条可扫描要点")
    if quantified:
        strengths.append(f"已有 {quantified} 处量化或结果证据")
    return (
        "本地简历诊断（无需 API Key）\n"
        f"基础信息：{len(lines)} 行正文，目标岗位：{target_role or '未设置'}。\n"
        f"已有基础：{'；'.join(strengths) if strengths else '已读取正文，建议补充可扫描结构。'}\n"
        f"优先修改：{'；'.join(issues[:3]) if issues else '结构和证据较完整，可继续针对具体 JD 做关键词对齐。'}\n"
        "下一步：可让 Agent 生成一份可编辑的优化草稿，确认后另存为新版本。"
    )


def model_resume_draft(
    client,
    content: str,
    target_role: str = "",
    jd: str = "",
    timeout: float = 32,
) -> ResumeDraft:
    """Ask a configured model for a factual rewrite; fall back to local rules."""
    target = str(target_role or "").strip() or "未指定"
    source = str(content or "").strip()
    result = client.chat(
        [
            {
                "role": "system",
                "content": (
                    "你是资深中文简历优化专家。请通读用户提供的完整原始简历，并重写为一份可直接保存和投递的完整简历正文。"
                    "必须覆盖原文中有效的教育、经历、项目、技能和证书信息，围绕目标岗位和 JD 优化语言、结构、动词、重点和可读性。"
                    "不得编造公司、项目、技术、指标、学历、职责、时间、结果或证书；原文没有数字时不要虚构数字。"
                    "只输出优化后的完整简历正文，不要解释、前言、Markdown 代码块或任何分析。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"目标岗位：{target}\n"
                    f"岗位 JD：{str(jd or '').strip() or '未提供'}\n\n"
                    "<完整原始简历>\n"
                    f"{source}\n"
                    "</完整原始简历>"
                ),
            },
        ],
        temperature=0.25,
        max_tokens=5000,
        timeout=timeout,
    )
    generated = str(result.get("content") or "").strip() if result.get("success") else ""
    if _is_complete_rewrite(source, generated):
        return ResumeDraft(generated, "model", ("已通读完整简历并重组表达", "保留原始经历事实", "按目标岗位调整重点"))
    return local_resume_draft(content, target_role)


def _is_complete_rewrite(source: str, generated: str) -> bool:
    if not generated or len(generated) < max(100, int(len(source) * 0.4)):
        return False
    lowered = generated.lower()
    if any(lowered.startswith(prefix) for prefix in ("当然", "下面是", "以下是", "优化后的", "简历优化")):
        return False
    critical_facts = re.findall(
        r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|1\d{10}|20\d{2}|\d+(?:%|个|次|项|人|天|万|k|K)",
        source,
    )
    compact_generated = re.sub(r"\s+", "", generated)
    return all(
        re.sub(r"\s+", "", fact) in compact_generated
        for fact in dict.fromkeys(critical_facts)
    )
