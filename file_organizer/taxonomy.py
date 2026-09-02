"""
Taxonomy definitions and clustering heuristics for File Organizer.
"""
import re

EXT_BUCKETS = {
    "Pictures": {
        "jpg", "jpeg", "png", "gif", "bmp", "webp", "heic", "heif",
        "tiff", "svg", "raw", "cr2", "nef", "avif"
    },
    "Videos": {
        "mp4", "mkv", "mov", "avi", "webm", "flv", "m4v", "wmv"
    },
    "Music": {
        "mp3", "flac", "wav", "ogg", "oga", "m4a", "aac", "wma", "opus"
    },
    "Documents": {
        "pdf", "docx", "doc", "odt", "ods", "odp", "txt", "md", "rtf",
        "xlsx", "xls", "csv", "pptx", "ppt", "epub", "mobi", "azw", "azw3",
    },
    "Archives": {
        "zip", "tar", "gz", "tgz", "bz2", "tbz2", "xz", "txz", "7z", "rar", "zst"
    },
    "Installers": {"deb", "rpm", "appimage", "run"},
    "DiskImages": {"iso", "img", "dmg"},
    "Fonts": {"ttf", "otf", "woff", "woff2"},
    "Code": {"json", "yaml", "yml", "toml", "ini", "conf"},
}

EXT_TO_BUCKET = {ext: bucket for bucket, exts in EXT_BUCKETS.items() for ext in exts}

SCREENSHOT_NAME_RE = re.compile(r"(screenshot|screen[\s_-]?shot|scrot|zrzut ekranu)", re.I)
SCREEN_RECORDING_NAME_RE = re.compile(r"(screen recording|screencast|obs|kazam|zoom_\d)", re.I)
IN_PROGRESS_RE = re.compile(r"\.(part|crdownload|tmp|download)$", re.I)
RECEIPT_NAME_RE = re.compile(r"(receipt|invoice|order[\s_-]?confirmation)", re.I)
MOD_JAR_RE = re.compile(
    r"(?:fabric|forge|quilt|neoforge|neoforged)[-_][\w.]+"
    r"|(?:^|[_-])(?:mc|minecraft|optifine|sodium|iris|lithium)(?:[-_]|$)"
    r"|mc[\d.]+",
    re.I,
)

CANDIDATE_DESTINATIONS = {
    "receipt-in-pictures": ["Documents/Receipts", "Pictures/Screenshots", "Pictures/Camera"],
    "video-no-signal": ["Videos", "Videos/Clips", "Videos/Movies"],
    "music-unknown-album": None,
    "music-no-artist": ["Music/Unsorted", "Downloads/Unsorted"],
    "pictures-ambiguous-cap": None,
    "unrecognized-extension": None,
}

YEAR_RE = re.compile(r"^(19|20)\d{2}$")

DEFAULT_CLUSTER_LEAF_NAMES = {
    "screenshots", "camera", "people", "unsorted", "receipts",
    "movies", "clips", "screen recordings", "installers", "archives",
    "disk images", "diskimages", "fonts", "code",
}
