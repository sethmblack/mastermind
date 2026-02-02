"""Persona loader module for loading personas from the AI-Personas repository."""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class PersonaSkill:
    """A skill that a persona can use."""
    name: str
    trigger: str
    use_when: str
    description: Optional[str] = None


@dataclass
class Persona:
    """A persona loaded from the AI-Personas repository."""
    name: str
    display_name: str
    prompt: str
    domain: Optional[str] = None
    domains: List[str] = field(default_factory=list)
    era: Optional[str] = None
    voice_profile: Optional[str] = None
    core_philosophy: Optional[str] = None
    methodology: Optional[str] = None
    signature_quotes: List[str] = field(default_factory=list)
    skills: List[PersonaSkill] = field(default_factory=list)
    expertise_summary: Optional[str] = None
    bio: Optional[str] = None
    _full_prompt_section: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert persona to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "prompt": self.prompt,
            "domain": self.domain,
            "domains": self.domains,
            "era": self.era,
            "voice_profile": self.voice_profile,
            "core_philosophy": self.core_philosophy,
            "methodology": self.methodology,
            "signature_quotes": self.signature_quotes[:3],
            "skills": [
                {"name": s.name, "trigger": s.trigger, "use_when": s.use_when}
                for s in self.skills
            ],
            "expertise_summary": self.expertise_summary,
            "bio": self.bio,
        }

    def get_system_prompt(self) -> str:
        """Get the system prompt for this persona."""
        if self._full_prompt_section:
            return self._full_prompt_section
        return self.prompt


class PersonaLoader:
    """Loads personas from the AI-Personas repository."""

    def __init__(self, personas_path: Optional[Path] = None):
        """Initialize the loader with a path to the personas directory."""
        self.personas_path = personas_path or Path(settings.personas_path)
        self._personas: Dict[str, Persona] = {}
        self._loaded = False

    def load_all(self) -> Dict[str, Persona]:
        """Load all personas from the directory."""
        if self._loaded:
            return self._personas

        if not self.personas_path.exists():
            logger.warning(f"Personas path does not exist: {self.personas_path}")
            self._loaded = True
            return self._personas

        for persona_dir in self.personas_path.iterdir():
            if not persona_dir.is_dir():
                continue
            if persona_dir.name.startswith("."):
                continue

            prompt_file = persona_dir / "PROMPT.md"
            if not prompt_file.exists():
                continue

            try:
                persona = self._load_persona(persona_dir)
                if persona:
                    self._personas[persona.name] = persona
            except Exception as e:
                logger.error(f"Error loading persona {persona_dir.name}: {e}")

        self._loaded = True
        logger.info(f"Loaded {len(self._personas)} personas from {self.personas_path}")
        return self._personas

    def _load_persona(self, persona_dir: Path) -> Optional[Persona]:
        """Load a single persona from a directory."""
        prompt_file = persona_dir / "PROMPT.md"
        content = prompt_file.read_text(encoding="utf-8")

        name = persona_dir.name
        display_name = self._extract_display_name(content, name)
        domain = self._extract_domain_info(content)
        domains = self._extract_domains(content, persona_dir)
        era = self._extract_era(content)
        voice_profile = self._extract_section(content, "Voice Profile")
        core_philosophy = self._extract_section(content, "Core Philosophy")
        methodology = self._extract_section(content, "Methodology")
        signature_quotes = self._extract_quotes(content)
        skills = self._extract_skills(content)
        prompt_block = self._extract_prompt_block(content)
        bio = self._extract_bio(content)

        # Load expertise summary if available
        expertise_summary = None
        expertise_file = persona_dir / "expertise.md"
        if expertise_file.exists():
            expertise_summary = expertise_file.read_text(encoding="utf-8").strip()

        return Persona(
            name=name,
            display_name=display_name,
            prompt=content,
            domain=domain,
            domains=domains,
            era=era,
            voice_profile=voice_profile,
            core_philosophy=core_philosophy,
            methodology=methodology,
            signature_quotes=signature_quotes,
            skills=skills,
            expertise_summary=expertise_summary,
            bio=bio,
            _full_prompt_section=prompt_block,
        )

    def _extract_display_name(self, content: str, folder_name: str) -> str:
        """Extract display name from the first heading."""
        match = re.search(r"^#\s+(.+?)(?:\s+Expert)?$", content, re.MULTILINE)
        if match:
            name = match.group(1).strip()
            # Remove trailing "Expert" if present
            name = re.sub(r"\s+Expert$", "", name)
            return name
        # Fallback: convert folder name to title case
        return folder_name.replace("-", " ").title()

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract content of a markdown section."""
        pattern = rf"##\s+{re.escape(section_name)}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_quotes(self, content: str) -> List[str]:
        """Extract blockquotes from content."""
        quotes = []
        pattern = r'>\s*"([^"]+)"'
        for match in re.finditer(pattern, content):
            quotes.append(match.group(1).strip())
        return quotes

    def _extract_skills(self, content: str) -> List[PersonaSkill]:
        """Extract skills from markdown table."""
        skills = []
        # Look for skills table
        table_pattern = r"\|\s*Skill\s*\|\s*Trigger\s*\|\s*Use When\s*\|.*?\n\|[-\s|]+\|\n((?:\|[^\n]+\|\n?)+)"
        match = re.search(table_pattern, content, re.IGNORECASE)
        if match:
            rows = match.group(1).strip().split("\n")
            for row in rows:
                cells = [c.strip() for c in row.split("|") if c.strip()]
                if len(cells) >= 3:
                    skills.append(PersonaSkill(
                        name=cells[0],
                        trigger=cells[1],
                        use_when=cells[2],
                    ))
        return skills

    def _extract_domain_info(self, content: str) -> Optional[str]:
        """Extract domain/category from content."""
        match = re.search(r"\*\*Category:\*\*\s*(.+?)(?:\n|$)", content)
        if match:
            return match.group(1).strip()
        return None

    def _extract_domains(self, content: str, persona_dir: Path) -> List[str]:
        """Extract all domains a persona belongs to."""
        domains = []
        # Check if there's a domains field
        match = re.search(r"\*\*Domains:\*\*\s*(.+?)(?:\n|$)", content)
        if match:
            domains_str = match.group(1).strip()
            domains = [d.strip() for d in domains_str.split(",")]

        # Also check the domain from Category
        category = self._extract_domain_info(content)
        if category and category not in domains:
            domains.insert(0, category)

        return domains

    def _extract_era(self, content: str) -> Optional[str]:
        """Extract era from content."""
        match = re.search(r"\*\*Era:\*\*\s*(.+?)(?:\n|$)", content)
        if match:
            return match.group(1).strip()
        return None

    def _extract_bio(self, content: str) -> Optional[str]:
        """Extract biographical description from content."""
        # Look for a bio section or the first paragraph after the heading
        bio_section = self._extract_section(content, "Bio")
        if bio_section:
            return bio_section

        bio_section = self._extract_section(content, "Biography")
        if bio_section:
            return bio_section

        # Try to get first substantial paragraph after metadata
        lines = content.split("\n")
        in_content = False
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                in_content = True
                continue
            if in_content and line and not line.startswith("**") and not line.startswith("|") and not line.startswith(">"):
                if len(line) > 50:
                    return line
        return None

    def _extract_prompt_block(self, content: str) -> Optional[str]:
        """Extract embedded prompt block from triple backticks."""
        match = re.search(r"```\n?(.*?)\n?```", content, re.DOTALL)
        if match:
            block = match.group(1).strip()
            if block.lower().startswith("you "):
                return block
        return None

    def get_all_personas(self) -> List[Persona]:
        """Get all personas as a list."""
        if not self._loaded:
            self.load_all()
        return list(self._personas.values())

    def get_persona(self, name: str) -> Optional[Persona]:
        """Get a persona by name."""
        if not self._loaded:
            self.load_all()

        # Normalize the name
        normalized = self._normalize_name(name)

        # Try exact match first
        if normalized in self._personas:
            return self._personas[normalized]

        # Try case-insensitive match
        for persona_name, persona in self._personas.items():
            if persona_name.lower() == normalized.lower():
                return persona

        return None

    def _normalize_name(self, name: str) -> str:
        """Normalize a persona name to internal format."""
        # Convert "AG Lafley" or "Albert Einstein" to "ag-lafley" or "albert-einstein"
        return name.lower().replace(" ", "-")

    def get_all_domains(self) -> List[str]:
        """Get all unique domains."""
        if not self._loaded:
            self.load_all()

        domains = set()
        for persona in self._personas.values():
            if persona.domain:
                domains.add(persona.domain)
            for d in persona.domains:
                domains.add(d)

        return sorted(list(domains))

    def get_personas_by_domain(self, domain: str) -> List[Persona]:
        """Get all personas in a domain."""
        if not self._loaded:
            self.load_all()

        result = []
        domain_lower = domain.lower()
        for persona in self._personas.values():
            if persona.domain and persona.domain.lower() == domain_lower:
                result.append(persona)
            elif any(d.lower() == domain_lower for d in persona.domains):
                result.append(persona)

        return result

    def search_personas(self, query: str, limit: int = 10) -> List[Persona]:
        """Search personas by name or other attributes."""
        if not self._loaded:
            self.load_all()

        query_lower = query.lower()
        results = []

        for persona in self._personas.values():
            score = 0

            # Name match
            if query_lower in persona.name.lower():
                score += 10
            if query_lower in persona.display_name.lower():
                score += 10

            # Domain match
            if persona.domain and query_lower in persona.domain.lower():
                score += 5

            # Voice profile match
            if persona.voice_profile and query_lower in persona.voice_profile.lower():
                score += 2

            # Bio match
            if persona.bio and query_lower in persona.bio.lower():
                score += 2

            if score > 0:
                results.append((score, persona))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)

        return [p for _, p in results[:limit]]


# Global loader instance
_loader: Optional[PersonaLoader] = None


def get_persona_loader() -> PersonaLoader:
    """Get the global persona loader instance."""
    global _loader
    if _loader is None:
        _loader = PersonaLoader()
    return _loader
