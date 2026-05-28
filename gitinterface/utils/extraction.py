import httpx
import base64
import asyncio

# only these
CODE_EXTENSIONS = frozenset({
    # Python
    ".py", ".pyi",
    # JavaScript / TypeScript
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    # Web
    ".html", ".css", ".scss", ".sass",
    # Backend
    ".go", ".rs", ".java", ".kt", ".scala",
    ".c", ".cpp", ".h", ".hpp", ".cs",
    ".rb", ".php", ".swift",
    # Shell
    ".sh", ".bash", ".zsh",
    # Config / infra (useful for repo understanding)
    ".json", ".yaml", ".yml", ".toml", ".env.example",
    ".dockerfile", ".tf",
    # Docs
    ".md", ".rst",
    # SQL
    ".sql",
})

# skip
SKIP_DIRS = frozenset({
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "env", "dist", "build", ".next", ".nuxt", "coverage",
    "vendor", ".idea", ".vscode", "migrations",
})

def clean_paths(paths: list[str]) -> list[str]:
    cleaned = []
    for path in paths:
        parts = path.split("/")

        # Skip
        if any(part in SKIP_DIRS for part in parts[:-1]):
            continue

        # white
        ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext in CODE_EXTENSIONS:
            cleaned.append(path)

    return cleaned

async def fetch_file(client: httpx.AsyncClient, username: str, repo_name: str, path: str) -> str | None:
    """Fetch and decode a single file. Returns formatted string or None on failure."""
    try:
        response = await client.get(
            f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}",
            timeout=15.0
        )
        if response.status_code != 200:
            return None

        data = response.json()
        if "content" not in data:
            return None

        decoded = base64.b64decode(data["content"]).decode("utf-8", errors="replace")

        # Structured format — LLM understands file boundaries clearly
        return f"### File: {path}\n```\n{decoded}\n```"

    except Exception:
        return None

async def extract_contents(
    paths: list[str],
    username: str,
    repo_name: str
) -> list[str]:

    if not paths or not username or not repo_name:
        return []

    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_file(client, username, repo_name, path)
            for path in paths
        ]

        results = await asyncio.gather(*tasks)

    return [r for r in results if r]
# async def extract_contents(paths: list[str], username: str, repo_name: str) -> str:
#     """
#     Fetch all files concurrently and return one structured string for LLM input.
#     """
#     if not paths or not username or not repo_name:
#         return ""
#
#     # One client for all requests — connection pooling
#     async with httpx.AsyncClient() as client:
#         tasks = [fetch_file(client, username, repo_name, path) for path in paths]
#
#         # Concurrently fetch all files
#         results = await asyncio.gather(*tasks)
#
#     # Filter failed fetches and join into one LLM-ready string
#     file_contents = [r for r in results if r is not None]
#     return "\n\n".join(file_contents)

def create_chunks(
    files: list[str],
    max_chars: int = 15000
) -> list[str]:

    chunks = []
    current_chunk = ""

    for file in files:

        # If single file exceeds limit
        if len(file) > max_chars:

            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            for i in range(0, len(file), max_chars):
                chunks.append(file[i:i+max_chars])

            continue

        # Normal packing
        if len(current_chunk) + len(file) > max_chars:
            chunks.append(current_chunk)
            current_chunk = file
        else:
            current_chunk += "\n\n" + file

    if current_chunk:
        chunks.append(current_chunk)

    return chunks