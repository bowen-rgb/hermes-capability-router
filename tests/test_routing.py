from plugin.annotation import AnnotationEngine, AnnotationReviewQueue
from plugin.discovery import DiscoveryEngine
from plugin.github_discovery import GitHubDiscovery
from plugin.commands import capability_review_command
from plugin.semantic_router import SemanticRouter
from plugin.models import AnnotationDraft, Capability, Implementation
from plugin.registry import CapabilityRegistry
from plugin.routing import CapabilityResolver
from plugin.storage import CapabilityStore
from plugin import register


def test_routes_chinese_ocr_request() -> None:
    decision = CapabilityResolver(CapabilityRegistry.from_default_file()).route("帮我提取这张截图里的文字")
    assert decision.scene == "vision"
    assert decision.intent == "text_extraction"
    assert decision.capability is not None
    assert decision.capability.capability_id == "vision.image_text_extraction"


def test_routes_image_understanding_request() -> None:
    decision = CapabilityResolver(CapabilityRegistry.from_default_file()).route("这张图片里有什么？")
    assert decision.scene == "vision"
    assert decision.intent == "image_understanding"
    assert decision.capability is not None
    assert decision.capability.capability_id == "vision.image_understanding"


def test_routes_french_ocr_request() -> None:
    decision = CapabilityResolver(CapabilityRegistry.from_default_file()).route(
        "Extrais le texte de cette capture d'écran."
    )
    assert decision.scene == "vision"
    assert decision.intent == "text_extraction"
    assert decision.capability is not None
    assert decision.capability.capability_id == "vision.image_text_extraction"


def test_routes_french_image_understanding_request() -> None:
    decision = CapabilityResolver(CapabilityRegistry.from_default_file()).route(
        "Qu'y a-t-il dans cette image ?"
    )
    assert decision.scene == "vision"
    assert decision.intent == "image_understanding"
    assert decision.capability is not None
    assert decision.capability.capability_id == "vision.image_understanding"


def test_routes_traditional_chinese_ocr_request() -> None:
    decision = CapabilityResolver(CapabilityRegistry.from_default_file()).route(
        "請辨識這張截圖裡的文字。"
    )
    assert decision.scene == "vision"
    assert decision.intent == "text_extraction"


def test_routes_french_unaccented_ocr_request() -> None:
    decision = CapabilityResolver(CapabilityRegistry.from_default_file()).route(
        "Lis le texte de cette capture d'ecran."
    )
    assert decision.scene == "vision"
    assert decision.intent == "text_extraction"


def test_plugin_registers_only_supported_hermes_hooks() -> None:
    class FakeContext:
        def __init__(self) -> None:
            self.hooks: list[str] = []

        def register_hook(self, name, callback) -> None:  # noqa: ANN001
            assert callable(callback)
            self.hooks.append(name)

        def register_command(self, name, callback, **kwargs) -> None:  # noqa: ANN001
            assert name == "capability-review"
            assert callable(callback)

    context = FakeContext()
    register(context)
    assert context.hooks == ["pre_llm_call", "pre_tool_call", "post_tool_call"]


def test_approved_annotation_draft_becomes_runtime_capability(tmp_path) -> None:  # noqa: ANN001
    capability = Capability(
        capability_id="audio.speech_to_text",
        name="Speech to text",
        description="Transcribe audio into text.",
        scenes=("audio",),
        intents=("speech_to_text",),
        tags=("transcription",),
        implementations=(
            Implementation("whisper-local", "Whisper local", "model", "local_inference", availability="installed"),
        ),
    )
    store = CapabilityStore(tmp_path / "capabilities.sqlite3")
    AnnotationReviewQueue(store).approve(AnnotationDraft("local_model", "C:/models/whisper", capability, confidence=0.88))
    assert store.get("audio.speech_to_text") == capability


def test_discovery_and_annotation_keep_registration_separate(tmp_path) -> None:  # noqa: ANN001
    plugin_dir = tmp_path / "plugins" / "paddleocr-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        "name: PaddleOCR Plugin\ndescription: OCR for screenshots\n", encoding="utf-8"
    )
    record = DiscoveryEngine().discover_hermes_plugins(plugin_dir.parent)[0]
    draft = AnnotationEngine().annotate(
        source_type=record.source_type,
        source_location=record.source_location,
        name=record.name,
        description=record.description,
        interface=record.interface,
    )
    assert draft.status == "pending_review"
    assert draft.capability.capability_id == "vision.image_text_extraction"


def test_semantic_router_can_use_embedding_backend_for_a_paraphrase() -> None:
    class FakeEmbeddings:
        def similarities(self, query, candidates):  # noqa: ANN001
            assert "屏幕" in query
            return tuple(0.91 if "OCR" in candidate else 0.22 for candidate in candidates)

    match = SemanticRouter(embedding_backend=FakeEmbeddings()).route(
        "把屏幕上的字弄出来",
        "vision",
        CapabilityRegistry.from_default_file().capabilities,
    )
    assert match.intent == "text_extraction"
    assert match.confidence == 0.91


def test_github_discovery_reads_metadata_and_readme_without_network() -> None:
    class FakeFetcher:
        def get_text(self, url):  # noqa: ANN001
            if url.endswith("/readme"):
                return '{"content": "T0NSIHRvb2xraXQgZm9yIGltYWdlcy4="}'
            return '{"name": "PaddleOCR", "description": "OCR toolkit"}'

    record = GitHubDiscovery(FakeFetcher()).discover("https://github.com/PaddlePaddle/PaddleOCR")
    assert record.name == "PaddleOCR"
    assert "OCR toolkit" in record.description


def test_pending_annotation_draft_is_persisted(tmp_path) -> None:  # noqa: ANN001
    store = CapabilityStore(tmp_path / "capabilities.sqlite3")
    draft = AnnotationEngine().annotate(
        source_type="github_repository",
        source_location="https://github.com/PaddlePaddle/PaddleOCR",
        name="PaddleOCR",
        description="OCR toolkit",
    )
    draft_id = AnnotationReviewQueue(store).submit(draft)
    pending = store.list_drafts("pending_review")
    assert pending[0][0] == draft_id
    assert pending[0][1].capability.capability_id == "vision.image_text_extraction"


def test_review_command_lists_and_approves_pending_draft(tmp_path) -> None:  # noqa: ANN001
    store = CapabilityStore(tmp_path / "capabilities.sqlite3")
    queue = AnnotationReviewQueue(store)
    queue.submit(
        AnnotationEngine().annotate(
            source_type="github_repository",
            source_location="https://github.com/PaddlePaddle/PaddleOCR",
            name="PaddleOCR",
            description="OCR toolkit",
        )
    )
    assert "PaddleOCR" in capability_review_command(store, queue, "")
    result = capability_review_command(store, queue, "approve 1")
    assert "Approved Image text extraction" in result
    assert store.get("vision.image_text_extraction") is not None


def test_review_command_marks_wrong_tag_and_keeps_draft_visible(tmp_path) -> None:  # noqa: ANN001
    store = CapabilityStore(tmp_path / "capabilities.sqlite3")
    queue = AnnotationReviewQueue(store)
    queue.submit(
        AnnotationEngine().annotate(
            source_type="github_repository",
            source_location="https://github.com/example/ambiguous-image-tool",
            name="Ambiguous image tool",
            description="Image helper",
        )
    )
    result = capability_review_command(store, queue, "mark-wrong 1 github_repository wrong source tag")
    assert "Marked tag 'github_repository' as incorrect" in result
    listing = capability_review_command(store, queue, "")
    assert "needs correction" in listing
    assert "github_repository" in listing
    assert "wrong source tag" in listing


def test_review_command_edits_tags_and_applies_preset(tmp_path) -> None:  # noqa: ANN001
    store = CapabilityStore(tmp_path / "capabilities.sqlite3")
    queue = AnnotationReviewQueue(store)
    queue.submit(
        AnnotationEngine().annotate(
            source_type="cli",
            source_location="C:/bin/image-reader.exe",
            name="Image reader",
            description="Reads image text",
        )
    )
    assert "Updated tags" in capability_review_command(store, queue, "set-tags 1 custom tag, needs-review")
    assert "Applied preset" in capability_review_command(
        store, queue, "apply-preset 1 vision.image_text_extraction"
    )
    draft = store.list_drafts()[0][1]
    assert draft.capability.capability_id == "vision.image_text_extraction"
    assert "ocr" in draft.capability.tags


def test_correction_must_be_resolved_before_approval(tmp_path) -> None:  # noqa: ANN001
    store = CapabilityStore(tmp_path / "capabilities.sqlite3")
    queue = AnnotationReviewQueue(store)
    queue.submit(AnnotationEngine().annotate(
        source_type="github_repository",
        source_location="https://github.com/example/reader",
        name="Reader",
        description="Image helper",
    ))
    capability_review_command(store, queue, "mark-wrong 1 github_repository incorrect tag")
    assert "Resolve or remove" in capability_review_command(store, queue, "approve 1")
    capability_review_command(store, queue, "set-tags 1 image helper")
    assert "Approved" in capability_review_command(store, queue, "approve 1")


def test_review_command_shows_preset_categories(tmp_path) -> None:  # noqa: ANN001
    store = CapabilityStore(tmp_path / "capabilities.sqlite3")
    queue = AnnotationReviewQueue(store)
    assert "vision.image_text_extraction" in capability_review_command(store, queue, "presets")
