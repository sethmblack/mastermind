"""Persona API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from ...personas.loader import get_persona_loader

router = APIRouter()


class PersonaSkillResponse(BaseModel):
    """Skill in API response."""
    name: str
    trigger: str
    use_when: str


class PersonaSummary(BaseModel):
    """Summary of a persona for list views."""
    name: str
    display_name: str
    description: Optional[str] = None  # Brief description for tooltip
    domain: Optional[str] = None
    domains: List[str] = []
    era: Optional[str] = None
    voice_preview: Optional[str] = None


class PersonaDetail(BaseModel):
    """Full persona details."""
    name: str
    display_name: str
    voice_profile: Optional[str] = None
    core_philosophy: Optional[str] = None
    methodology: Optional[str] = None
    domain: Optional[str] = None
    domains: List[str] = []
    era: Optional[str] = None
    skills: List[PersonaSkillResponse] = []
    signature_quotes: List[str] = []
    expertise_summary: Optional[str] = None
    prompt_preview: Optional[str] = None


class DomainInfo(BaseModel):
    """Domain with persona count."""
    name: str
    display_name: str
    persona_count: int


@router.get("/", response_model=List[PersonaSummary])
async def list_personas(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    search: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(100, ge=1, le=300),
    offset: int = Query(0, ge=0),
):
    """List all available personas with optional filtering."""
    loader = get_persona_loader()

    if search:
        personas = loader.search_personas(search, limit=limit + offset)
        personas = personas[offset:offset + limit]
    elif domain:
        personas = loader.get_personas_by_domain(domain)
        personas = personas[offset:offset + limit]
    else:
        personas = loader.get_all_personas()
        personas = sorted(personas, key=lambda p: p.display_name)
        personas = personas[offset:offset + limit]

    def get_description(p) -> Optional[str]:
        """Get the biographical description for a persona."""
        # Use the bio field if available (extracted from PROMPT.md)
        if p.bio:
            return p.bio

        # Fallback to expertise summary
        if p.expertise_summary:
            # Get first sentence
            first_sentence = p.expertise_summary.split('.')[0]
            if len(first_sentence) > 20:
                return first_sentence + '.'

        return None

    return [
        PersonaSummary(
            name=p.name,
            display_name=p.display_name,
            description=get_description(p),
            domain=p.domain,
            domains=p.domains,
            era=p.era,
            voice_preview=p.voice_profile[:200] if p.voice_profile else None,
        )
        for p in personas
    ]


@router.get("/count")
async def get_persona_count():
    """Get total number of personas."""
    loader = get_persona_loader()
    return {"count": len(loader.get_all_personas())}


@router.get("/domains", response_model=List[DomainInfo])
async def list_domains():
    """List all available domains with persona counts."""
    loader = get_persona_loader()
    domains = loader.get_all_domains()

    # Sort case-insensitively for better UX
    domain_infos = [
        DomainInfo(
            name=domain,
            display_name=domain.replace("-", " ").title(),
            persona_count=len(loader.get_personas_by_domain(domain)),
        )
        for domain in domains
    ]
    return sorted(domain_infos, key=lambda d: d.display_name.lower())


@router.get("/{persona_name}", response_model=PersonaDetail)
async def get_persona(persona_name: str):
    """Get detailed information about a specific persona."""
    loader = get_persona_loader()
    persona = loader.get_persona(persona_name)

    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_name}' not found")

    # Get first 500 chars of prompt as preview
    prompt_preview = None
    if persona.prompt:
        prompt_preview = persona.prompt[:500] + "..." if len(persona.prompt) > 500 else persona.prompt

    return PersonaDetail(
        name=persona.name,
        display_name=persona.display_name,
        voice_profile=persona.voice_profile,
        core_philosophy=persona.core_philosophy,
        methodology=persona.methodology,
        domain=persona.domain,
        domains=persona.domains,
        era=persona.era,
        skills=[
            PersonaSkillResponse(
                name=s.name,
                trigger=s.trigger,
                use_when=s.use_when,
            )
            for s in persona.skills
        ],
        signature_quotes=persona.signature_quotes[:5],
        expertise_summary=persona.expertise_summary,
        prompt_preview=prompt_preview,
    )


@router.get("/{persona_name}/prompt")
async def get_persona_prompt(persona_name: str):
    """Get the full system prompt for a persona."""
    loader = get_persona_loader()
    persona = loader.get_persona(persona_name)

    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_name}' not found")

    return {
        "persona_name": persona_name,
        "display_name": persona.display_name,
        "full_prompt": persona.prompt,
        "system_prompt": persona.get_system_prompt(),
    }


@router.get("/skills/{skill_name}/prompt")
async def get_skill_prompt(skill_name: str):
    """Get the full prompt for a skill."""
    from pathlib import Path
    from ...config import settings

    # Skills are in the shared skills directory
    skills_path = Path(settings.skills_path) if hasattr(settings, 'skills_path') else Path("/app/data/personas/skills")
    skill_dir = skills_path / skill_name
    prompt_file = skill_dir / "PROMPT.md"

    if not prompt_file.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    content = prompt_file.read_text(encoding="utf-8")

    # Extract display name from first heading
    import re
    match = re.search(r"^#\s+(.+?)$", content, re.MULTILINE)
    display_name = match.group(1).strip() if match else skill_name.replace("-", " ").title()

    return {
        "skill_name": skill_name,
        "display_name": display_name,
        "prompt": content,
    }
