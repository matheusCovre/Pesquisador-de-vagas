from io import BytesIO
from typing import Literal
from xml.sax.saxutils import escape

import pymupdf
from docx import Document
from docx.shared import Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from app.schemas.resume import ResumeData
from app.services.file_storage_service import save_resume_file
from app.services.guardrail_service import assert_private_text, load_approved_source, verify_resume

NAVY_HEX = "#1A3654"
TAG_HEX = "#3F5B74"
MUTED_HEX = "#485867"
BODY_HEX = "#232C34"
LINE_HEX = "#CBD5E1"

NAVY_RGB = RGBColor(0x1A, 0x36, 0x54)
TAG_RGB = RGBColor(0x3F, 0x5B, 0x74)
MUTED_RGB = RGBColor(0x48, 0x58, 0x67)
BODY_RGB = RGBColor(0x23, 0x2C, 0x34)


def _contact_line(resume: ResumeData) -> str:
    parts = [
        p
        for p in [
            resume.candidate.location,
            resume.candidate.phone,
            resume.candidate.email,
            resume.candidate.linkedin,
            resume.candidate.github,
        ]
        if p
    ]
    return "  |  ".join(parts)


def _split_skill(skill: str) -> tuple[str, str] | None:
    if ":" not in skill:
        return None
    category, rest = skill.split(":", 1)
    if category.strip() and rest.strip():
        return category.strip(), rest.strip()
    return None


def _experience_heading(role: str, company: str, period: str, location: str) -> str:
    loc_suffix = f" · {location}" if location else ""
    return f"{company} | {role} | {period}{loc_suffix}"


def _project_heading(title: str, technologies: list[str], status: str | None) -> str:
    parts = [title]
    if technologies:
        parts.append(" · ".join(technologies))
    if status == "in_development":
        parts.append("em desenvolvimento")
    return " | ".join(parts)


def generate_and_save_resume(
    resume: ResumeData, file_format: Literal["docx", "pdf"]
) -> tuple[bytes, str]:
    """Gera o documento e preserva uma cópia antes de disponibilizá-lo."""
    if file_format == "pdf":
        content = generate_pdf(resume)
    elif file_format == "docx":
        content = generate_docx(resume)
    else:
        raise ValueError("Formato de currículo inválido.")
    text = (
        extract_text_from_pdf(content) if file_format == "pdf" else extract_text_from_docx(content)
    )
    candidate = load_approved_source()["candidate"]
    assert_private_text(text, (candidate["email"],), (candidate["phone"],))
    file_id = save_resume_file(content, file_format)
    return content, file_id


def generate_docx(resume: ResumeData) -> bytes:
    """Gera um arquivo Word (.docx) alinhado ao kit de currículos-mestre."""
    verify_resume(resume)
    doc = Document()

    section = doc.sections[0]
    section.page_width = Pt(612)
    section.page_height = Pt(792)
    section.top_margin = Pt(33.75)
    section.bottom_margin = Pt(31.2)
    section.left_margin = Pt(48.2)
    section.right_margin = Pt(48.2)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Aptos"
    normal_style.font.size = Pt(9)
    normal_style.font.color.rgb = BODY_RGB
    normal_style.paragraph_format.space_after = Pt(2.2)
    normal_style.paragraph_format.line_spacing = 1.06

    def add_section_heading(label: str) -> None:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(7.2)
        p.paragraph_format.space_after = Pt(2.7)
        r = p.add_run(label)
        r.bold = True
        r.font.name = "Aptos"
        r.font.size = Pt(10)
        r.font.color.rgb = NAVY_RGB

    def add_subheading(text: str) -> None:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(3.0)
        p.paragraph_format.space_after = Pt(1.4)
        r = p.add_run(text)
        r.bold = True
        r.font.name = "Aptos"
        r.font.size = Pt(9)
        r.font.color.rgb = NAVY_RGB

    name_p = doc.add_paragraph()
    name_p.paragraph_format.space_after = Pt(3.0)
    name_run = name_p.add_run(resume.candidate.name)
    name_run.bold = True
    name_run.font.name = "Aptos"
    name_run.font.size = Pt(17)
    name_run.font.color.rgb = NAVY_RGB

    tag_p = doc.add_paragraph()
    tag_p.paragraph_format.space_after = Pt(3.0)
    tag_run = tag_p.add_run(resume.candidate.headline)
    tag_run.bold = True
    tag_run.font.name = "Aptos"
    tag_run.font.size = Pt(9)
    tag_run.font.color.rgb = TAG_RGB

    contact_text = _contact_line(resume)
    if contact_text:
        contact_p = doc.add_paragraph()
        contact_p.paragraph_format.space_after = Pt(3.0)
        contact_run = contact_p.add_run(contact_text)
        contact_run.font.name = "Aptos"
        contact_run.font.size = Pt(8.5)
        contact_run.font.color.rgb = MUTED_RGB

    add_section_heading("PERFIL PROFISSIONAL")
    doc.add_paragraph(resume.summary)

    if resume.skills:
        add_section_heading("COMPETÊNCIAS TÉCNICAS")
        for skill in resume.skills:
            split = _split_skill(skill)
            if split:
                category, desc = split
                p = doc.add_paragraph()
                cat_run = p.add_run(f"{category}: ")
                cat_run.bold = True
                cat_run.font.color.rgb = NAVY_RGB
                p.add_run(desc)
            else:
                doc.add_paragraph(f"• {skill}")

    if resume.experiences:
        add_section_heading("EXPERIÊNCIA PROFISSIONAL")
        for exp in resume.experiences:
            add_subheading(_experience_heading(exp.role, exp.company, exp.period, exp.location))
            for item in exp.highlights:
                doc.add_paragraph(f"• {item}")

    if resume.projects:
        add_section_heading("PROJETOS SELECIONADOS")
        for proj in resume.projects:
            add_subheading(_project_heading(proj.title, proj.technologies, proj.status))
            doc.add_paragraph(f"• {proj.description}")

    if resume.education:
        add_section_heading("FORMAÇÃO ACADÊMICA")
        for edu in resume.education:
            doc.add_paragraph(f"{edu.degree} — {edu.institution} | {edu.period}")

    if resume.research:
        add_section_heading("PESQUISA E APRESENTAÇÕES")
        for item in resume.research:
            doc.add_paragraph(item)

    if resume.languages:
        add_section_heading("IDIOMAS")
        doc.add_paragraph(" | ".join(resume.languages))

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def generate_pdf(resume: ResumeData) -> bytes:
    """Gera um arquivo PDF compacto (1 página) alinhado ao kit de currículos-mestre."""
    verify_resume(resume)

    def escape_values(value):
        if isinstance(value, str):
            return escape(value)
        if isinstance(value, list):
            return [escape_values(item) for item in value]
        if isinstance(value, dict):
            return {key: escape_values(item) for key, item in value.items()}
        return value

    # Dados nunca viram marcação XML/HTML do ReportLab.
    resume = ResumeData.model_validate(escape_values(resume.model_dump()))
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=48.2,
        leftMargin=48.2,
        topMargin=33.75,
        bottomMargin=31.2,
    )

    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        "CVName",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=18,
        textColor=colors.HexColor(NAVY_HEX),
        spaceAfter=2,
    )
    tag_style = ParagraphStyle(
        "CVTag",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.8,
        leading=11,
        textColor=colors.HexColor(TAG_HEX),
        spaceAfter=2,
    )
    contact_style = ParagraphStyle(
        "CVSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=10.5,
        textColor=colors.HexColor(MUTED_HEX),
        spaceAfter=4,
    )
    section_style = ParagraphStyle(
        "CVHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=9.6,
        leading=11.5,
        textColor=colors.HexColor(NAVY_HEX),
        spaceBefore=6.5,
        spaceAfter=2.2,
    )
    sub_style = ParagraphStyle(
        "CVSub",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.8,
        leading=11,
        textColor=colors.HexColor(NAVY_HEX),
        spaceBefore=2.5,
        spaceAfter=1.2,
    )
    body_style = ParagraphStyle(
        "CVBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.6,
        leading=10.8,
        textColor=colors.HexColor(BODY_HEX),
        spaceAfter=1.8,
    )

    def add_section(label: str) -> None:
        story.append(Paragraph(label, section_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(LINE_HEX)))
        story.append(Spacer(1, 2.5))

    story = [
        Paragraph(resume.candidate.name, name_style),
        Paragraph(resume.candidate.headline, tag_style),
    ]

    contact_text = _contact_line(resume)
    if contact_text:
        story.append(Paragraph(contact_text, contact_style))

    add_section("PERFIL PROFISSIONAL")
    story.append(Paragraph(resume.summary, body_style))

    if resume.skills:
        add_section("COMPETÊNCIAS TÉCNICAS")
        for skill in resume.skills:
            split = _split_skill(skill)
            if split:
                category, desc = split
                story.append(
                    Paragraph(
                        f'<font color="{NAVY_HEX}"><b>{category}:</b></font> {desc}',
                        body_style,
                    )
                )
            else:
                story.append(Paragraph(f"• {skill}", body_style))

    if resume.experiences:
        add_section("EXPERIÊNCIA PROFISSIONAL")
        for exp in resume.experiences:
            story.append(
                Paragraph(
                    _experience_heading(exp.role, exp.company, exp.period, exp.location),
                    sub_style,
                )
            )
            for h in exp.highlights:
                story.append(Paragraph(f"• {h}", body_style))

    if resume.projects:
        add_section("PROJETOS SELECIONADOS")
        for proj in resume.projects:
            story.append(
                Paragraph(
                    _project_heading(proj.title, proj.technologies, proj.status),
                    sub_style,
                )
            )
            story.append(Paragraph(f"• {proj.description}", body_style))

    if resume.education:
        add_section("FORMAÇÃO ACADÊMICA")
        for edu in resume.education:
            story.append(
                Paragraph(
                    f"{edu.degree} — {edu.institution} | {edu.period}",
                    body_style,
                )
            )

    if resume.research:
        add_section("PESQUISA E APRESENTAÇÕES")
        for item in resume.research:
            story.append(Paragraph(item, body_style))

    if resume.languages:
        add_section("IDIOMAS")
        story.append(Paragraph(" | ".join(resume.languages), body_style))

    pdf.build(story)
    return buffer.getvalue()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrai texto de um PDF enviado para análise."""
    with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc).strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extrai texto de um arquivo Word (.docx) enviado para análise."""
    doc = Document(BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
