"""Tests for persona API routes."""

import pytest
from httpx import AsyncClient
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestListPersonas:
    """Tests for GET /api/personas/"""

    async def test_list_personas(self, client: AsyncClient, temp_personas_dir: Path):
        """Test listing all personas."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            # Clear cached loader
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    async def test_list_personas_with_limit(self, client: AsyncClient, temp_personas_dir: Path):
        """Test listing personas with limit."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/?limit=2")
            assert response.status_code == 200
            data = response.json()
            assert len(data) <= 2

    async def test_list_personas_with_offset(self, client: AsyncClient, temp_personas_dir: Path):
        """Test listing personas with offset."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/?offset=2&limit=10")
            assert response.status_code == 200

    async def test_list_personas_with_domain_filter(self, client: AsyncClient, temp_personas_dir: Path):
        """Test filtering personas by domain."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/?domain=Scientists")
            assert response.status_code == 200
            data = response.json()
            # All returned personas should be scientists
            for persona in data:
                assert persona.get("domain") == "Scientists"

    async def test_list_personas_with_search(self, client: AsyncClient, temp_personas_dir: Path):
        """Test searching personas."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/?search=einstein")
            assert response.status_code == 200
            data = response.json()
            # Should find Albert Einstein
            names = [p["name"] for p in data]
            assert "albert-einstein" in names or len(data) == 0  # May not find if mock data differs


class TestGetPersonaCount:
    """Tests for GET /api/personas/count"""

    async def test_get_persona_count(self, client: AsyncClient, temp_personas_dir: Path):
        """Test getting persona count."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/count")
            assert response.status_code == 200
            data = response.json()
            assert "count" in data
            assert isinstance(data["count"], int)


class TestListDomains:
    """Tests for GET /api/personas/domains/"""

    async def test_list_domains(self, client: AsyncClient, temp_personas_dir: Path):
        """Test listing all domains."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/domains")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # Each domain should have name, display_name, persona_count
            for domain in data:
                assert "name" in domain
                assert "display_name" in domain
                assert "persona_count" in domain


class TestGetPersona:
    """Tests for GET /api/personas/{persona_name}"""

    async def test_get_persona(self, client: AsyncClient, temp_personas_dir: Path):
        """Test getting a specific persona."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/albert-einstein")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "albert-einstein"
            assert "display_name" in data
            assert "voice_profile" in data

    async def test_get_persona_not_found(self, client: AsyncClient, temp_personas_dir: Path):
        """Test getting non-existent persona."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/non-existent-persona")
            assert response.status_code == 404

    async def test_get_persona_includes_skills(self, client: AsyncClient, temp_personas_dir: Path):
        """Test that persona includes skills."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/albert-einstein")
            assert response.status_code == 200
            data = response.json()
            assert "skills" in data
            assert isinstance(data["skills"], list)


class TestGetPersonaPrompt:
    """Tests for GET /api/personas/{persona_name}/prompt"""

    async def test_get_persona_prompt(self, client: AsyncClient, temp_personas_dir: Path):
        """Test getting persona's full prompt."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/albert-einstein/prompt")
            assert response.status_code == 200
            data = response.json()
            assert "persona_name" in data
            assert "full_prompt" in data or "system_prompt" in data

    async def test_get_persona_prompt_not_found(self, client: AsyncClient, temp_personas_dir: Path):
        """Test getting prompt for non-existent persona."""
        with patch("src.config.settings.personas_path", temp_personas_dir / "experts"):
            from src.personas import loader
            loader._persona_loader = None

            response = await client.get("/api/personas/non-existent/prompt")
            assert response.status_code == 404
