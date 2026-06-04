from __future__ import annotations

from pathlib import Path

from ingestion.youtube_etl import (
    FeedVideo,
    TranscriptSegment,
    load_processed_ids,
    parse_youtube_feed,
    render_transcript_markdown,
    slugify,
    write_transcript_artifact,
)


def test_parse_youtube_feed_extracts_video_metadata() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
          xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <yt:videoId>abc123</yt:videoId>
        <title>Video de Teste</title>
        <link rel="alternate" href="https://www.youtube.com/watch?v=abc123"/>
        <published>2026-06-04T10:00:00+00:00</published>
      </entry>
    </feed>
    """

    videos = parse_youtube_feed(xml)

    assert videos == [
        FeedVideo(
            video_id="abc123",
            title="Video de Teste",
            url="https://www.youtube.com/watch?v=abc123",
            published_at="2026-06-04T10:00:00+00:00",
        )
    ]


def test_render_transcript_markdown_has_ingest_article_contract() -> None:
    video = FeedVideo("abc123", "Titulo \"Especial\"", "https://youtube.test/watch?v=abc123")
    transcript = [TranscriptSegment("Primeira fala", start=3), TranscriptSegment("Segunda fala")]

    markdown = render_transcript_markdown(video, transcript)

    assert "source_kind: youtube_transcript" in markdown
    assert "video_id: abc123" in markdown
    assert "# Titulo \"Especial\"" in markdown
    assert "[00:03] Primeira fala" in markdown
    assert "Segunda fala" in markdown
    assert "`/ingest-article`" in markdown


def test_write_transcript_artifact_and_history_helpers(tmp_path: Path) -> None:
    video = FeedVideo("abc123", "Meu Video de Teste", "https://youtube.test/watch?v=abc123")
    output = write_transcript_artifact(tmp_path, video, [TranscriptSegment("conteudo")])

    assert output.name == f"youtube-abc123-{slugify('Meu Video de Teste')}.md"
    assert output.exists()

    history = tmp_path / "historico.txt"
    history.write_text("abc123\n\nxyz789\n", encoding="utf-8")
    assert load_processed_ids(history) == {"abc123", "xyz789"}
