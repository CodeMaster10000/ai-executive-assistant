"""Cover letter agent: generates a cover letter from CV + JD."""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base import LLMAgent


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so text reads as plain prose."""
    # Remove headers (### Title -> Title)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # Remove bullet prefixes
    text = re.sub(r"^[\-\*]\s+", "", text, flags=re.MULTILINE)
    # Collapse multiple newlines into a single space
    text = re.sub(r"\n+", " ", text)
    # Collapse multiple spaces
    text = re.sub(r"  +", " ", text)
    return text.strip()


# Section headers that should NOT be treated as a person's name
_SECTION_HEADERS = frozenset({
    "professional summary", "summary", "experience", "education",
    "skills", "certifications", "projects", "contact", "objective",
    "work experience", "technical skills", "profile", "about",
    "about me", "references", "languages", "interests", "hobbies",
})


def _extract_name_from_cv(cv_text: str) -> str | None:
    """Try to extract the person's name from the first line of CV text.

    CVs typically start with the person's name before any section header.
    Returns None if no plausible name is found.
    """
    if not cv_text or not cv_text.strip():
        return None
    for line in cv_text.strip().splitlines():
        line = re.sub(r"^#{1,6}\s+", "", line).strip()
        line = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", line).strip()
        if not line:
            continue
        normalized = line.lower()
        if normalized in _SECTION_HEADERS:
            continue
        # A name is typically 2-4 short words, all alphabetic
        words = line.split()
        if 2 <= len(words) <= 4 and all(w.isalpha() for w in words):
            return line
        # If the first non-empty, non-header line isn't a name, stop looking
        break
    return None


class CoverLetterAgent(LLMAgent):
    """Generates a tailored cover letter from CV content, job description, and profile data."""

    agent_name = "cover_letter"

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate a cover letter from the CV, JD, and profile information in state."""
        cv_content = state.get("cv_content", "")
        jd_text = state.get("jd_text", "")
        job_opportunity = state.get("job_opportunity", {})
        profile_name = state.get("profile_name", "")
        profile_targets = state.get("profile_targets", [])
        profile_skills = state.get("profile_skills", [])
        profile_constraints = state.get("profile_constraints", [])

        if self._llm is None:
            return self._mock_cover_letter(
                profile_name, profile_skills, job_opportunity,
                cv_content, jd_text, profile_targets, profile_constraints,
            )

        system_prompt = self._get_system_prompt()

        sections = []
        if profile_name:
            sections.append(f"## Candidate Name\n{profile_name}")
        if profile_targets:
            sections.append(
                f"## Career Targets\n{', '.join(profile_targets)}"
            )
        if profile_skills:
            sections.append(f"## Key Skills\n{', '.join(profile_skills)}")
        if profile_constraints:
            sections.append(
                f"## Constraints/Preferences\n{', '.join(profile_constraints)}"
            )
        sections.append(f"## CV Summary\n{cv_content}")
        sections.append(f"## Job Description\n{jd_text}")
        if job_opportunity:
            sections.append(
                f"## Opportunity Details\n{json.dumps(job_opportunity)}"
            )

        user_content = "\n\n".join(sections)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        response = await self._llm.ainvoke(messages)
        content = response.content.replace("\u2014", ",").replace("\u2013", ",")
        return {"cover_letter_content": content}

    @staticmethod
    def _build_hook_paragraph(
        name: str,
        title: str,
        company: str,
        cv_content: str,
    ) -> str:
        """Build the opening paragraph using CV context if available."""
        if cv_content and cv_content.strip():
            cv_clean = _strip_markdown(cv_content)
            cv_snippet = cv_clean[:200].rsplit(" ", 1)[0]
            return (
                f"Dear {company} Hiring Team,\n\n"
                "Having built my career around delivering production-grade "
                f"software solutions, I was immediately drawn to the {title} "
                f"role at {company}. My background, which includes "
                f"{cv_snippet}, has given me a strong foundation in solving "
                "the kinds of technical challenges this position demands. "
                "I am confident that my hands-on experience positions me "
                "to contribute meaningfully from day one."
            )
        return (
            f"Dear {company} Hiring Team,\n\n"
            "Having built my career around delivering production-grade "
            f"software solutions, I was immediately drawn to the {title} "
            f"role at {company}. My track record of designing, building, "
            "and shipping scalable systems across multiple domains has "
            "given me a strong foundation in solving the kinds of "
            "technical challenges this position demands. I am confident "
            "that my hands-on experience positions me to contribute "
            "meaningfully from day one."
        )

    @staticmethod
    def _build_skills_paragraph(
        profile_skills: list[str],
        jd_text: str,
    ) -> str:
        """Build the skills alignment paragraph from skills and JD."""
        if profile_skills:
            primary = profile_skills[:3]
            secondary = profile_skills[3:6]
            skills_para = (
                f"My core expertise in {', '.join(primary)} aligns directly "
                "with the technical requirements of this role. I have "
                "applied these skills across production systems, "
                "consistently delivering solutions that meet both "
                "performance benchmarks and business objectives."
            )
            if secondary:
                skills_para += (
                    " I also bring hands-on experience with "
                    f"{', '.join(secondary)}, which I have used across "
                    "multiple production environments to deliver measurable "
                    "improvements in system reliability, deployment "
                    "velocity, and overall engineering quality."
                )
            if jd_text:
                jd_preview = _strip_markdown(jd_text)[:150].rsplit(" ", 1)[0]
                skills_para += (
                    " Reviewing the role's requirements around "
                    f"{jd_preview}, I see a strong match with the projects "
                    "I have led and the technical problems I have solved "
                    "throughout my career."
                )
            return skills_para
        if jd_text:
            jd_preview = _strip_markdown(jd_text)[:200].rsplit(" ", 1)[0]
            return (
                f"The role's focus on {jd_preview} resonates strongly with "
                "my professional experience. I have consistently delivered "
                "solutions in similar technical domains, building systems "
                "that balance performance, maintainability, and business "
                "impact. I take pride in writing clean, well-tested code "
                "and designing architectures that stand the test of time."
            )
        return (
            "Throughout my career, I have consistently delivered "
            "solutions that balance technical excellence with business "
            "impact. I bring a strong foundation in software "
            "engineering principles, system design, and collaborative "
            "development practices that enable teams to ship reliable "
            "software at scale. I take pride in writing clean, "
            "well-tested code and designing architectures that are "
            "both maintainable and performant."
        )

    @staticmethod
    def _build_culture_paragraph(
        profile_targets: list[str] | None,
        profile_constraints: list[str] | None,
        description: str,
        company: str,
        title: str,
    ) -> str:
        """Build the culture fit paragraph from targets and constraints."""
        culture_parts: list[str] = []
        if profile_targets:
            culture_parts.append(
                f"My career trajectory toward {', '.join(profile_targets[:3])} "
                "aligns well with the direction of this role"
            )
        if profile_constraints:
            culture_parts.append(
                "I value a work environment that supports "
                f"{', '.join(profile_constraints[:2])}"
            )
        if description:
            desc_preview = _strip_markdown(description)[:120].rsplit(" ", 1)[0]
            culture_parts.append(
                f"the opportunity to work on {desc_preview} is "
                "particularly compelling"
            )

        if culture_parts:
            return (
                f"{culture_parts[0]}, and "
                + ". ".join(culture_parts[1:])
                + ". I thrive in environments where engineering rigor meets "
                "real-world problem solving, and I am eager to bring that "
                f"mindset to the {company} team. I believe that the best "
                "software is built by teams that combine deep technical "
                "skill with strong communication and a shared commitment "
                "to quality."
            )
        return (
            "I am drawn to teams that value engineering rigor, "
            "continuous improvement, and collaborative problem solving. "
            f"The opportunity to contribute to {company}'s technical "
            "challenges while growing alongside a talented team is "
            "what makes this role stand out to me. I believe that the "
            "best software is built by teams that combine deep "
            "technical skill with strong communication and a shared "
            "commitment to delivering real value to users."
        )

    @staticmethod
    def _mock_cover_letter(
        profile_name: str,
        profile_skills: list[str],
        job_opportunity: dict[str, Any],
        cv_content: str = "",
        jd_text: str = "",
        profile_targets: list[str] | None = None,
        profile_constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        name = _extract_name_from_cv(cv_content) or profile_name or "The Candidate"
        title = job_opportunity.get("title", "the position")
        company = job_opportunity.get("company", "your organization")
        description = job_opportunity.get("description", "")

        hook = CoverLetterAgent._build_hook_paragraph(
            name, title, company, cv_content,
        )
        skills_para = CoverLetterAgent._build_skills_paragraph(
            profile_skills, jd_text,
        )
        culture_para = CoverLetterAgent._build_culture_paragraph(
            profile_targets, profile_constraints, description, company, title,
        )

        # Paragraph 4: Call to action
        closing = (
            "I would welcome the chance to discuss how my experience and "
            f"skills can contribute to {company}'s goals. I am genuinely "
            f"excited about the technical challenges this {title} role "
            "presents and would appreciate the opportunity to speak with "
            "you about how I can add value to your team. Please do not "
            "hesitate to reach out at your convenience to arrange a "
            "conversation.\n\n"
            f"Best regards,\n{name}"
        )

        content = f"{hook}\n\n{skills_para}\n\n{culture_para}\n\n{closing}"
        content = content.replace("\u2014", ",").replace("\u2013", ",")
        return {"cover_letter_content": content}
