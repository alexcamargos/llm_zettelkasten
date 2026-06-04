"""YouTube playlist transcript ETL pipeline.

This module automates the fetching of new videos from a YouTube playlist RSS
feed, fetches their transcripts using the YouTube Transcript API, converts them
to formatted Markdown files, and stores them in the raw articles directory. It
also tracks processed videos to avoid duplicate downloads.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from config import Settings, load_settings
from logger import configure_logging, get_logger

YOUTUBE_FEED_URL = "https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"


@dataclass(frozen=True)
class FeedVideo:
    """Represents a YouTube video metadata retrieved from an RSS feed.

    Attributes:
        video_id: The unique identifier of the YouTube video.
        title: The title of the video.
        url: The direct watch URL of the video.
        published_at: Optional string representation of the publication timestamp.
    """

    video_id: str
    title: str
    url: str
    published_at: str | None = None


@dataclass(frozen=True)
class TranscriptSegment:
    """Represents a single text segment of a video transcript.

    Attributes:
        text: The transcribed text.
        start: Optional start time of the segment in seconds.
        duration: Optional duration of the segment in seconds.
    """

    text: str
    start: float | None = None
    duration: float | None = None


def playlist_feed_url(playlist_id: str) -> str:
    """Format the YouTube RSS feed URL for a given playlist ID.

    Args:
        playlist_id: The YouTube playlist ID.

    Returns:
        str: The formatted feed URL.
    """
    return YOUTUBE_FEED_URL.format(playlist_id=playlist_id)


def load_processed_ids(history_path: Path) -> set[str]:
    """Load the set of already processed YouTube video IDs from the history file.

    Args:
        history_path: Path to the text file tracking ingested IDs.

    Returns:
        set[str]: A set of unique video ID strings.
    """
    if not history_path.exists():
        return set()
    return {
        line.strip()
        for line in history_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def append_processed_id(history_path: Path, video_id: str) -> None:
    """Append a newly processed YouTube video ID to the history file.

    Args:
        history_path: Path to the text file tracking ingested IDs.
        video_id: The video ID to record.

    Returns:
        None
    """
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(f"{video_id}\n")


def parse_youtube_feed(xml_content: str) -> list[FeedVideo]:
    """Parse raw YouTube RSS feed XML content to extract video metadata.

    Args:
        xml_content: The raw XML string from the feed.

    Returns:
        list[FeedVideo]: A list of FeedVideo metadata objects.
    """
    root = ElementTree.fromstring(xml_content)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    videos: list[FeedVideo] = []
    for entry in root.findall("atom:entry", ns):
        video_id = _text(entry.find("yt:videoId", ns))
        title = _text(entry.find("atom:title", ns))
        link = entry.find("atom:link", ns)
        url = link.attrib.get("href", "") if link is not None else ""
        published_at = _text(entry.find("atom:published", ns)) or None
        if video_id and title and url:
            videos.append(
                FeedVideo(
                    video_id=video_id,
                    title=title,
                    url=url,
                    published_at=published_at,
                )
            )
    return videos


def fetch_feed_videos(playlist_id: str) -> list[FeedVideo]:
    """Fetch and parse feed videos for a playlist using the feedparser library.

    Args:
        playlist_id: The YouTube playlist ID.

    Returns:
        list[FeedVideo]: A list of FeedVideo metadata objects from the playlist feed.
    """
    import feedparser

    parsed_feed = feedparser.parse(playlist_feed_url(playlist_id))
    videos: list[FeedVideo] = []
    for entry in parsed_feed.entries:
        video_id = getattr(entry, "yt_videoid", None) or _video_id_from_url(
            getattr(entry, "link", "")
        )
        if not video_id:
            continue
        videos.append(
            FeedVideo(
                video_id=video_id,
                title=getattr(entry, "title", video_id),
                url=getattr(entry, "link", f"https://www.youtube.com/watch?v={video_id}"),
                published_at=getattr(entry, "published", None),
            )
        )
    return videos


def fetch_transcript(
    video_id: str,
    languages: tuple[str, ...] = ("pt", "pt-BR", "en"),
) -> list[TranscriptSegment]:
    """Fetch the transcript for a YouTube video in the preferred languages.

    Args:
        video_id: The unique YouTube video ID.
        languages: Priority tuple of language codes. Defaults to ("pt", "pt-BR", "en").

    Returns:
        list[TranscriptSegment]: List of retrieved transcript segments.
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    raw_segments = YouTubeTranscriptApi.get_transcript(video_id, languages=list(languages))
    return [
        TranscriptSegment(
            text=str(segment.get("text", "")).strip(),
            start=_float_or_none(segment.get("start")),
            duration=_float_or_none(segment.get("duration")),
        )
        for segment in raw_segments
        if str(segment.get("text", "")).strip()
    ]


def render_transcript_markdown(video: FeedVideo, transcript: list[TranscriptSegment]) -> str:
    """Render YouTube video and transcript data into formatted Markdown text.

    Args:
        video: The video metadata object.
        transcript: The transcript segment objects list.

    Returns:
        str: Formatted Markdown string representing the transcript.
    """
    retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [
        "---",
        f'title: "{_yaml_escape(video.title)}"',
        "source_kind: youtube_transcript",
        f"video_id: {video.video_id}",
        f'url: "{video.url}"',
        f'retrieved_at: "{retrieved_at}"',
    ]
    if video.published_at:
        lines.append(f'published_at: "{_yaml_escape(video.published_at)}"')
    lines.extend(
        [
            "---",
            "",
            f"# {video.title}",
            "",
            "Transcricao bruta extraida automaticamente do YouTube. Este arquivo deve ser "
            "tratado pelo fluxo `/ingest-youtube` antes de entrar no cofre Zettelkasten.",
            "",
            "## Transcricao",
            "",
        ]
    )
    lines.extend(_format_transcript_lines(transcript))
    return "\n".join(lines).rstrip() + "\n"


def transcript_output_path(raw_articles_path: Path, video: FeedVideo) -> Path:
    """Determine the file output path for a video transcript markdown file.

    Args:
        raw_articles_path: Target directory path for storing transcripts.
        video: The video metadata object.

    Returns:
        Path: Output markdown file Path.
    """
    return raw_articles_path / f"youtube-{video.video_id}-{slugify(video.title)}.md"


def write_transcript_artifact(
    raw_articles_path: Path,
    video: FeedVideo,
    transcript: list[TranscriptSegment],
) -> Path:
    """Write the rendered transcript markdown content to a local file.

    Args:
        raw_articles_path: Target directory path for storing transcripts.
        video: The video metadata object.
        transcript: The list of transcript segments.

    Returns:
        Path: The file Path where the transcript was saved.
    """
    raw_articles_path.mkdir(parents=True, exist_ok=True)
    output_path = transcript_output_path(raw_articles_path, video)
    output_path.write_text(
        render_transcript_markdown(video, transcript),
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def ingest_youtube_playlist(
    settings: Settings,
    *,
    dry_run: bool = False,
    limit: int | None = None,
) -> list[Path]:
    """Ingest new video transcripts from the configured YouTube playlist.

    Fetches the playlist feed, filters out already processed video IDs,
    retrieves their transcripts, writes the Markdown files, and logs the history.

    Args:
        settings: The project configuration settings.
        dry_run: If True, detects candidates without downloading or saving transcripts.
        limit: Maximum number of new videos to process in this run.

    Returns:
        list[Path]: A list of file Paths created during ingestion.

    Raises:
        ValueError: If YOUTUBE_PLAYLIST_ID is not configured in settings.
    """
    if not settings.youtube_playlist_id:
        raise ValueError("YOUTUBE_PLAYLIST_ID nao configurado.")

    logger = get_logger()
    processed_ids = load_processed_ids(settings.ingestion_history_path)
    candidates = [
        video
        for video in fetch_feed_videos(settings.youtube_playlist_id)
        if video.video_id not in processed_ids
    ]
    if limit is not None:
        candidates = candidates[:limit]

    created: list[Path] = []
    for video in candidates:
        logger.info("youtube_etl_video_detected id={} title={}", video.video_id, video.title)
        if dry_run:
            continue
        transcript = fetch_transcript(video.video_id)
        created_path = write_transcript_artifact(settings.raw_articles_path, video, transcript)
        append_processed_id(settings.ingestion_history_path, video.video_id)
        created.append(created_path)
        logger.info("youtube_etl_artifact_created path={}", created_path)
    return created


def slugify(value: str) -> str:
    """Slugify a string for filesystem compatibility.

    Args:
        value: Input string to slugify.

    Returns:
        str: Slugified string containing lowercase letters, numbers and hyphens.
    """
    normalized = value.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized[:80] or "video"


def main() -> None:
    """CLI execution entrypoint for the YouTube ETL.

    Parses command-line arguments and runs the playlist ingestion pipeline.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(
        description="Ingere transcricoes novas de uma playlist YouTube."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista videos novos sem escrever arquivos.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de videos processados.",
    )
    args = parser.parse_args()

    settings = load_settings(require_youtube=True)
    configure_logging(settings.logs_path)
    created = ingest_youtube_playlist(settings, dry_run=args.dry_run, limit=args.limit)
    if args.dry_run:
        get_logger().info("youtube_etl_dry_run_completed")
    else:
        get_logger().info("youtube_etl_completed created_count={}", len(created))


def _format_transcript_lines(transcript: list[TranscriptSegment]) -> list[str]:
    """Format transcript segments as timestamped strings.

    Args:
        transcript: List of TranscriptSegment objects.

    Returns:
        list[str]: Formatted timestamped transcript lines.
    """
    lines: list[str] = []
    for segment in transcript:
        if segment.start is None:
            lines.append(segment.text)
        else:
            lines.append(f"[{_format_seconds(segment.start)}] {segment.text}")
    return lines


def _format_seconds(value: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS format.

    Args:
        value: Number of seconds.

    Returns:
        str: Time representation string.
    """
    total_seconds = int(value)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _text(element: ElementTree.Element[str] | None) -> str:
    """Extract and strip XML element text.

    Args:
        element: ElementTree XML element.

    Returns:
        str: Stripted text content, or empty string.
    """
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _video_id_from_url(url: str) -> str | None:
    """Extract YouTube video ID from a watch URL query parameter.

    Args:
        url: The YouTube watch URL.

    Returns:
        str | None: The extracted 11-character video ID, or None if not matched.
    """
    match = re.search(r"[?&]v=([^&]+)", url)
    if match:
        return match.group(1)
    return None


def _float_or_none(value: Any) -> float | None:
    """Convert input to float, return None on failure.

    Args:
        value: Any input value.

    Returns:
        float | None: Parsed float value, or None if invalid.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _yaml_escape(value: str) -> str:
    """Escape backslashes and double quotes for safe YAML output.

    Args:
        value: Input string to escape.

    Returns:
        str: Escaped string.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


if __name__ == "__main__":
    main()
