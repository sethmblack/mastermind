"""Tests for persona loader module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.personas.loader import PersonaLoader, Persona, PersonaSkill, get_persona_loader


class TestPersona:
    """Tests for Persona dataclass."""

    def test_create_persona(self):
        """Test creating a persona."""
        persona = Persona(
            name="test-persona",
            display_name="Test Persona",
            prompt="You are a test persona.",
            domain="Testing",
            era="Modern",
            voice_profile="Speaks clearly.",
            core_philosophy="Test everything.",
            methodology="Write tests.",
            signature_quotes=["Testing is key."],
        )
        assert persona.name == "test-persona"
        assert persona.display_name == "Test Persona"
        assert persona.prompt == "You are a test persona."

    def test_persona_required_fields(self):
        """Test persona with only required fields."""
        persona = Persona(
            name="minimal",
            display_name="Minimal",
            prompt="A minimal persona.",
        )
        assert persona.name == "minimal"
        assert persona.domain is None
        assert persona.skills == []
        assert persona.signature_quotes == []

    def test_persona_to_dict(self):
        """Test converting persona to dict."""
        persona = Persona(
            name="test",
            display_name="Test",
            prompt="Test prompt.",
            domain="Testing",
        )
        d = persona.to_dict()
        assert d["name"] == "test"
        assert d["display_name"] == "Test"
        assert d["domain"] == "Testing"

    def test_persona_get_system_prompt_with_prompt(self):
        """Test getting system prompt from prompt field."""
        persona = Persona(
            name="test",
            display_name="Test Persona",
            prompt="You are Test Persona.",
        )
        prompt = persona.get_system_prompt()
        assert "You are Test Persona" in prompt

    def test_persona_get_system_prompt_with_full_prompt_section(self):
        """Test getting system prompt from _full_prompt_section."""
        persona = Persona(
            name="test",
            display_name="Test Persona",
            prompt="Full markdown content",
            _full_prompt_section="You embody the spirit of a test persona.",
        )
        prompt = persona.get_system_prompt()
        assert "You embody" in prompt

    def test_persona_to_dict_includes_skills(self):
        """Test that to_dict includes skills."""
        skill = PersonaSkill(
            name="testing",
            trigger="/test",
            use_when="When testing is needed",
        )
        persona = Persona(
            name="test",
            display_name="Test",
            prompt="Test prompt.",
            skills=[skill],
        )
        d = persona.to_dict()
        assert len(d["skills"]) == 1
        assert d["skills"][0]["name"] == "testing"

    def test_persona_to_dict_limits_quotes(self):
        """Test that to_dict limits signature quotes to 3."""
        persona = Persona(
            name="test",
            display_name="Test",
            prompt="Test prompt.",
            signature_quotes=["Quote 1", "Quote 2", "Quote 3", "Quote 4", "Quote 5"],
        )
        d = persona.to_dict()
        assert len(d["signature_quotes"]) == 3


class TestPersonaSkill:
    """Tests for PersonaSkill dataclass."""

    def test_create_skill(self):
        """Test creating a skill."""
        skill = PersonaSkill(
            name="analysis",
            trigger="/analyze",
            use_when="When analysis is needed",
        )
        assert skill.name == "analysis"
        assert skill.trigger == "/analyze"
        assert skill.use_when == "When analysis is needed"

    def test_skill_with_description(self):
        """Test skill with optional description."""
        skill = PersonaSkill(
            name="test-skill",
            trigger="/test",
            use_when="When testing",
            description="A detailed description of the skill.",
        )
        assert skill.description == "A detailed description of the skill."

    def test_skill_defaults(self):
        """Test skill default values."""
        skill = PersonaSkill(
            name="minimal",
            trigger="/min",
            use_when="Always",
        )
        assert skill.description is None


class TestPersonaLoader:
    """Tests for PersonaLoader."""

    def test_create_loader(self, temp_personas_dir: Path):
        """Test creating a persona loader."""
        loader = PersonaLoader(personas_path=temp_personas_dir / "experts")
        assert loader is not None
        assert loader.personas_path == temp_personas_dir / "experts"

    def test_load_all_personas(self, temp_personas_dir: Path):
        """Test loading personas from directory."""
        loader = PersonaLoader(personas_path=temp_personas_dir / "experts")
        personas = loader.load_all()
        assert isinstance(personas, dict)

    def test_get_all_personas(self, temp_personas_dir: Path):
        """Test getting all personas as list."""
        loader = PersonaLoader(personas_path=temp_personas_dir / "experts")
        personas = loader.get_all_personas()
        assert isinstance(personas, list)

    def test_get_persona_by_name(self, temp_personas_dir: Path):
        """Test getting persona by name."""
        loader = PersonaLoader(personas_path=temp_personas_dir / "experts")
        # First load all
        loader.load_all()
        # Then try to get one
        all_personas = loader.get_all_personas()
        if all_personas:
            first_persona = all_personas[0]
            persona = loader.get_persona(first_persona.name)
            assert persona is not None
            assert persona.name == first_persona.name

    def test_get_nonexistent_persona(self, temp_personas_dir: Path):
        """Test getting non-existent persona returns None."""
        loader = PersonaLoader(personas_path=temp_personas_dir / "experts")
        persona = loader.get_persona("nonexistent-persona-xyz")
        assert persona is None

    def test_get_all_domains(self, temp_personas_dir: Path):
        """Test getting all domains."""
        loader = PersonaLoader(personas_path=temp_personas_dir / "experts")
        loader.load_all()
        domains = loader.get_all_domains()
        assert isinstance(domains, list)

    def test_search_personas(self, temp_personas_dir: Path):
        """Test searching personas."""
        loader = PersonaLoader(personas_path=temp_personas_dir / "experts")
        loader.load_all()
        # Search for something
        results = loader.search_personas("a")
        assert isinstance(results, list)

    def test_search_with_limit(self, temp_personas_dir: Path):
        """Test search with result limit."""
        loader = PersonaLoader(personas_path=temp_personas_dir / "experts")
        loader.load_all()
        results = loader.search_personas("a", limit=2)
        assert len(results) <= 2

    def test_empty_directory(self, tmp_path: Path):
        """Test loading from empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        loader = PersonaLoader(personas_path=empty_dir)
        personas = loader.load_all()
        assert len(personas) == 0

    def test_invalid_directory(self, tmp_path: Path):
        """Test loading from non-existent directory."""
        loader = PersonaLoader(personas_path=tmp_path / "nonexistent")
        personas = loader.load_all()
        assert len(personas) == 0

    def test_lazy_loading(self, temp_personas_dir: Path):
        """Test that personas are lazy loaded."""
        loader = PersonaLoader(personas_path=temp_personas_dir / "experts")
        # Before calling load_all, _loaded should be False
        assert loader._loaded is False
        # After calling get_all_personas, should auto-load
        loader.get_all_personas()
        assert loader._loaded is True

    def test_caching(self, temp_personas_dir: Path):
        """Test that load_all returns cached results."""
        loader = PersonaLoader(personas_path=temp_personas_dir / "experts")
        result1 = loader.load_all()
        result2 = loader.load_all()
        # Should be the same dictionary object (cached)
        assert result1 is result2


class TestGetPersonaLoader:
    """Tests for get_persona_loader function."""

    def test_get_persona_loader_singleton(self):
        """Test that get_persona_loader returns singleton."""
        from src.personas import loader as loader_module

        # Reset the global
        original = loader_module._loader
        loader_module._loader = None

        try:
            loader1 = get_persona_loader()
            loader2 = get_persona_loader()
            assert loader1 is loader2
        finally:
            # Restore original
            loader_module._loader = original


class TestPersonaLoaderParsing:
    """Tests for PersonaLoader parsing methods."""

    def test_extract_display_name(self, tmp_path: Path):
        """Test extracting display name from markdown."""
        # Create a test persona
        persona_dir = tmp_path / "experts" / "test-persona"
        persona_dir.mkdir(parents=True)
        prompt_file = persona_dir / "PROMPT.md"
        prompt_file.write_text("# Test Persona Expert\n\nContent here.")

        loader = PersonaLoader(personas_path=tmp_path / "experts")
        content = prompt_file.read_text()
        display_name = loader._extract_display_name(content, "test-persona")
        assert "Test Persona" in display_name

    def test_extract_section(self, tmp_path: Path):
        """Test extracting a section from markdown."""
        # Create a test persona
        persona_dir = tmp_path / "experts" / "test-persona"
        persona_dir.mkdir(parents=True)
        prompt_file = persona_dir / "PROMPT.md"
        prompt_file.write_text("""# Test Persona

## Voice Profile

This is the voice profile content.

## Core Philosophy

This is the philosophy.
""")

        loader = PersonaLoader(personas_path=tmp_path / "experts")
        content = prompt_file.read_text()
        voice = loader._extract_section(content, "Voice Profile")
        assert voice is not None
        assert "voice profile content" in voice

    def test_extract_quotes(self, tmp_path: Path):
        """Test extracting quotes from markdown."""
        loader = PersonaLoader(personas_path=tmp_path)
        content = '''
> "First quote here"

Some text.

> "Second quote here"
'''
        quotes = loader._extract_quotes(content)
        assert len(quotes) == 2
        assert "First quote" in quotes[0]
        assert "Second quote" in quotes[1]

    def test_extract_skills_from_table(self, tmp_path: Path):
        """Test extracting skills from markdown table."""
        loader = PersonaLoader(personas_path=tmp_path)
        content = '''
## Available Skills

| Skill | Trigger | Use When |
|-------|---------|----------|
| Analysis | /analyze | When analysis needed |
| Summary | /summary | For summaries |
'''
        skills = loader._extract_skills(content)
        assert len(skills) == 2
        assert skills[0].name == "Analysis"
        assert skills[0].trigger == "/analyze"

    def test_extract_domain_info(self, tmp_path: Path):
        """Test extracting domain info."""
        loader = PersonaLoader(personas_path=tmp_path)
        content = "**Category:** Scientists\n**Era:** 20th Century"
        domain = loader._extract_domain_info(content)
        assert domain == "Scientists"

    def test_extract_era(self, tmp_path: Path):
        """Test extracting era info."""
        loader = PersonaLoader(personas_path=tmp_path)
        content = "**Category:** Scientists\n**Era:** 20th Century"
        era = loader._extract_era(content)
        assert era == "20th Century"

    def test_extract_prompt_block(self, tmp_path: Path):
        """Test extracting embedded prompt block."""
        loader = PersonaLoader(personas_path=tmp_path)
        content = '''
Some text.

```
You embody the spirit of a test persona who is great at testing.
```

More text.
'''
        prompt_block = loader._extract_prompt_block(content)
        assert prompt_block is not None
        assert "You embody" in prompt_block


class TestPersonaLoaderIntegration:
    """Integration tests for PersonaLoader."""

    def test_full_persona_loading(self, tmp_path: Path):
        """Test loading a complete persona."""
        # Create a complete persona directory
        persona_dir = tmp_path / "experts" / "test-expert"
        persona_dir.mkdir(parents=True)

        prompt_content = '''# Test Expert

**Category:** Testing
**Era:** Modern

## Voice Profile

Speaks with clarity and precision.

## Core Philosophy

Testing leads to quality.

## Available Skills

| Skill | Trigger | Use When |
|-------|---------|----------|
| Test | /test | When testing |

> "A quote"

```
You embody the spirit of a testing expert.
```
'''
        prompt_file = persona_dir / "PROMPT.md"
        prompt_file.write_text(prompt_content)

        # Load the persona
        loader = PersonaLoader(personas_path=tmp_path / "experts")
        personas = loader.load_all()

        assert "test-expert" in personas
        persona = personas["test-expert"]
        # Note: The loader strips "Expert" suffix from display names
        assert "Test" in persona.display_name
        assert persona.domain == "Testing"
        assert persona.voice_profile is not None
        assert len(persona.skills) == 1
        assert len(persona.signature_quotes) == 1

    def test_persona_with_expertise_file(self, tmp_path: Path):
        """Test loading persona with expertise.md file."""
        # Create persona with expertise file
        persona_dir = tmp_path / "experts" / "expert-with-expertise"
        persona_dir.mkdir(parents=True)

        (persona_dir / "PROMPT.md").write_text("# Expert With Expertise\n\nPrompt content.")
        (persona_dir / "expertise.md").write_text("This is the expertise summary.\n\nMore details here.")

        loader = PersonaLoader(personas_path=tmp_path / "experts")
        persona = loader.get_persona("expert-with-expertise")

        assert persona is not None
        assert persona.expertise_summary is not None
        assert "expertise summary" in persona.expertise_summary
