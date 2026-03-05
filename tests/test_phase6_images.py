"""
tests/test_phase6_images.py

Tests for Phase 6 — food image analysis.

The Gemini vision LLM is mocked so tests run offline and fast.
We test both endpoints (base64 JSON and multipart upload) plus
all the validation paths.

Run with:
  pytest tests/test_phase6_images.py -v
"""

from __future__ import annotations

import base64
import io
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base
from app import create_app
from dependencies import get_db
from schemas.image_schemas import ImageAnalysisResponse, IdentifiedFoodItemOut, NutritionEstimateOut

# ── SQLite test DB ────────────────────────────────────────────────────────────
SQLITE_URL = "sqlite:///./test_images.db"
engine_test = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine_test, autocommit=False, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def client():
    app = create_app()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    client.post("/auth/register", json={"name": "Image Tester", "password": "pass1234"})
    resp = client.post("/auth/login", json={"name": "Image Tester", "password": "pass1234"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_tiny_jpeg_b64() -> str:
    """
    A 1×1 pixel valid JPEG encoded as base64.
    Small enough to pass validation, real enough for the mime check.
    """
    # Minimal valid JPEG header bytes for a 1x1 white pixel
    jpeg_bytes = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
        b"C  C\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
        b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4"
        b"\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00"
        b"\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"
        b'"2\x81\x08\x14B\x91\xa1\xb1\xc1\t#3R\xf0\x15br\xd1'
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xff\xd9"
    )
    return base64.standard_b64encode(jpeg_bytes).decode("utf-8")


def _mock_analysis_response() -> ImageAnalysisResponse:
    return ImageAnalysisResponse(
        identified_items=[
            IdentifiedFoodItemOut(name="Grilled Chicken Breast", estimated_amount="200g", confidence="high"),
            IdentifiedFoodItemOut(name="Brown Rice",             estimated_amount="150g", confidence="high"),
            IdentifiedFoodItemOut(name="Steamed Broccoli",       estimated_amount="80g",  confidence="medium"),
        ],
        estimated_nutrition=NutritionEstimateOut(
            calories=520, protein_g=46.0, carbs_g=48.0, fat_g=11.0, fiber_g=7.0,
        ),
        meal_type_guess    = "lunch",
        analysis_notes     = "Sauce on chicken not clearly visible — calories may be slightly higher.",
        confidence_overall = "high",
        dish_summary       = "Grilled Chicken Breast, Brown Rice, Steamed Broccoli",
        log_id             = None,
        logged             = False,
    )


def _mock_analysis_with_log() -> ImageAnalysisResponse:
    r = _mock_analysis_response()
    return r.model_copy(update={"log_id": "log-auto-001", "logged": True})


# ═══════════════════════════════════════════════════════════════
# BASE64 JSON ENDPOINT — POST /images/analyse
# ═══════════════════════════════════════════════════════════════

class TestAnalyseBase64:

    def test_requires_auth(self, client):
        r = client.post("/images/analyse", json={
            "image_base64": _make_tiny_jpeg_b64(),
            "mime_type": "image/jpeg",
        })
        assert r.status_code == 401

    def test_analyse_success(self, client, auth_headers):
        mock_resp = _mock_analysis_response()
        with patch("api.routers.images.analyse_image_base64", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_resp
            r = client.post("/images/analyse", json={
                "image_base64": _make_tiny_jpeg_b64(),
                "mime_type": "image/jpeg",
            }, headers=auth_headers)

        assert r.status_code == 200
        data = r.json()
        assert len(data["identified_items"]) == 3
        assert data["identified_items"][0]["name"] == "Grilled Chicken Breast"
        assert data["estimated_nutrition"]["calories"] == 520
        assert data["estimated_nutrition"]["protein_g"] == 46.0
        assert data["meal_type_guess"] == "lunch"
        assert data["confidence_overall"] == "high"
        assert data["dish_summary"] == "Grilled Chicken Breast, Brown Rice, Steamed Broccoli"
        assert data["logged"] is False
        assert data["log_id"] is None

    def test_analyse_with_auto_log(self, client, auth_headers):
        mock_resp = _mock_analysis_with_log()
        with patch("api.routers.images.analyse_image_base64", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_resp
            r = client.post("/images/analyse", json={
                "image_base64": _make_tiny_jpeg_b64(),
                "mime_type":    "image/jpeg",
                "auto_log":     True,
                "log_date":     "2026-03-05",
                "meal_slot":    "lunch",
            }, headers=auth_headers)

        assert r.status_code == 200
        data = r.json()
        assert data["logged"] is True
        assert data["log_id"] == "log-auto-001"

    def test_invalid_mime_type(self, client, auth_headers):
        with patch("api.routers.images.analyse_image_base64", new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = ValueError("Unsupported image type 'image/gif'.")
            r = client.post("/images/analyse", json={
                "image_base64": _make_tiny_jpeg_b64(),
                "mime_type":    "image/gif",
            }, headers=auth_headers)
        assert r.status_code == 400

    def test_invalid_base64(self, client, auth_headers):
        with patch("api.routers.images.analyse_image_base64", new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = ValueError("Invalid base64 image data.")
            r = client.post("/images/analyse", json={
                "image_base64": "not-valid-base64!!!!",
                "mime_type":    "image/jpeg",
            }, headers=auth_headers)
        assert r.status_code == 400

    def test_llm_error_returns_500(self, client, auth_headers):
        with patch("api.routers.images.analyse_image_base64", new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = Exception("Gemini API quota exceeded")
            r = client.post("/images/analyse", json={
                "image_base64": _make_tiny_jpeg_b64(),
                "mime_type":    "image/jpeg",
            }, headers=auth_headers)
        assert r.status_code == 500

    def test_data_url_prefix_accepted(self, client, auth_headers):
        """Clients often send data:image/jpeg;base64,<data> — should be handled."""
        mock_resp = _mock_analysis_response()
        data_url = f"data:image/jpeg;base64,{_make_tiny_jpeg_b64()}"
        with patch("api.routers.images.analyse_image_base64", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_resp
            r = client.post("/images/analyse", json={
                "image_base64": data_url,
                "mime_type":    "image/jpeg",
            }, headers=auth_headers)
        # Service strips prefix — should succeed
        assert mock_fn.called

    def test_png_mime_type_accepted(self, client, auth_headers):
        mock_resp = _mock_analysis_response()
        with patch("api.routers.images.analyse_image_base64", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_resp
            r = client.post("/images/analyse", json={
                "image_base64": _make_tiny_jpeg_b64(),
                "mime_type":    "image/png",
            }, headers=auth_headers)
        assert mock_fn.called

    def test_response_has_all_fields(self, client, auth_headers):
        mock_resp = _mock_analysis_response()
        with patch("api.routers.images.analyse_image_base64", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_resp
            r = client.post("/images/analyse", json={
                "image_base64": _make_tiny_jpeg_b64(),
                "mime_type":    "image/jpeg",
            }, headers=auth_headers)

        data = r.json()
        required = [
            "identified_items", "estimated_nutrition", "meal_type_guess",
            "analysis_notes", "confidence_overall", "dish_summary",
            "log_id", "logged",
        ]
        for field in required:
            assert field in data, f"Missing response field: {field}"

        nutrition_fields = ["calories", "protein_g", "carbs_g", "fat_g"]
        for field in nutrition_fields:
            assert field in data["estimated_nutrition"], f"Missing nutrition field: {field}"

        item_fields = ["name", "estimated_amount", "confidence"]
        for item in data["identified_items"]:
            for field in item_fields:
                assert field in item, f"Missing item field: {field}"


# ═══════════════════════════════════════════════════════════════
# MULTIPART UPLOAD ENDPOINT — POST /images/upload
# ═══════════════════════════════════════════════════════════════

class TestUploadImage:

    def _make_upload_bytes(self) -> bytes:
        """Return raw JPEG bytes for upload testing."""
        return base64.b64decode(_make_tiny_jpeg_b64())

    def test_requires_auth(self, client):
        r = client.post(
            "/images/upload",
            files={"file": ("food.jpg", self._make_upload_bytes(), "image/jpeg")},
        )
        assert r.status_code == 401

    def test_upload_success(self, client, auth_headers):
        mock_resp = _mock_analysis_response()
        with patch("api.routers.images.analyse_image_upload", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_resp
            r = client.post(
                "/images/upload",
                files={"file": ("food.jpg", self._make_upload_bytes(), "image/jpeg")},
                headers=auth_headers,
            )

        assert r.status_code == 200
        data = r.json()
        assert data["estimated_nutrition"]["calories"] == 520
        assert data["confidence_overall"] == "high"

    def test_upload_with_auto_log_form(self, client, auth_headers):
        mock_resp = _mock_analysis_with_log()
        with patch("api.routers.images.analyse_image_upload", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_resp
            r = client.post(
                "/images/upload",
                files={"file": ("meal.jpg", self._make_upload_bytes(), "image/jpeg")},
                data={
                    "auto_log":  "true",
                    "log_date":  "2026-03-05",
                    "meal_slot": "dinner",
                },
                headers=auth_headers,
            )

        assert r.status_code == 200
        assert r.json()["logged"] is True

    def test_unsupported_file_type(self, client, auth_headers):
        r = client.post(
            "/images/upload",
            files={"file": ("image.gif", b"GIF89a...", "image/gif")},
            headers=auth_headers,
        )
        assert r.status_code == 415

    def test_empty_file_rejected(self, client, auth_headers):
        r = client.post(
            "/images/upload",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_png_accepted(self, client, auth_headers):
        mock_resp = _mock_analysis_response()
        with patch("api.routers.images.analyse_image_upload", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_resp
            r = client.post(
                "/images/upload",
                files={"file": ("photo.png", self._make_upload_bytes(), "image/png")},
                headers=auth_headers,
            )
        assert mock_fn.called

    def test_webp_accepted(self, client, auth_headers):
        mock_resp = _mock_analysis_response()
        with patch("api.routers.images.analyse_image_upload", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_resp
            r = client.post(
                "/images/upload",
                files={"file": ("photo.webp", self._make_upload_bytes(), "image/webp")},
                headers=auth_headers,
            )
        assert mock_fn.called

    def test_llm_error_returns_500(self, client, auth_headers):
        with patch("api.routers.images.analyse_image_upload", new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = Exception("Vision model error")
            r = client.post(
                "/images/upload",
                files={"file": ("food.jpg", self._make_upload_bytes(), "image/jpeg")},
                headers=auth_headers,
            )
        assert r.status_code == 500


# ═══════════════════════════════════════════════════════════════
# SERVICE UNIT TESTS — validation helpers
# ═══════════════════════════════════════════════════════════════

class TestServiceValidation:

    def test_validate_mime_accepted(self):
        from services.image_service import _validate_mime
        for mime in ["image/jpeg", "image/png", "image/webp"]:
            _validate_mime(mime)   # should not raise

    def test_validate_mime_rejected(self):
        from services.image_service import _validate_mime
        import pytest
        with pytest.raises(ValueError, match="Unsupported"):
            _validate_mime("image/gif")
        with pytest.raises(ValueError):
            _validate_mime("application/pdf")

    def test_validate_base64_clean(self):
        from services.image_service import _validate_base64
        b64 = _make_tiny_jpeg_b64()
        raw = _validate_base64(b64)
        assert isinstance(raw, bytes)
        assert len(raw) > 0

    def test_validate_base64_strips_data_url(self):
        from services.image_service import _validate_base64
        data_url = f"data:image/jpeg;base64,{_make_tiny_jpeg_b64()}"
        raw = _validate_base64(data_url)
        assert isinstance(raw, bytes)

    def test_validate_base64_invalid(self):
        from services.image_service import _validate_base64
        with pytest.raises(ValueError, match="Invalid base64"):
            _validate_base64("!!! not base64 !!!")

    def test_validate_image_size_pass(self):
        from services.image_service import _validate_image_size
        _validate_image_size(b"x" * 1000)   # 1 KB — fine

    def test_validate_image_size_fail(self):
        from services.image_service import _validate_image_size
        with pytest.raises(ValueError, match="too large"):
            _validate_image_size(b"x" * (11 * 1024 * 1024))   # 11 MB