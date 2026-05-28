import re
import json
import asyncio
import httpx
import httpx
from django.conf import settings
from groq import Groq

# async def analyze_repository(code: str):
#     """
#         result structure :
#             {
#               "summary": "",
#               "quality_score": 7,
#               "tech_stack": [
#               ],
#               "strengths": [
#               ],
#               "weaknesses": [
#               ]
#             }
#     """
#
#     url = "https://api.groq.com/openai/v1/chat/completions"
#
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"
#     }
#
#     prompt = f"""You are a senior software engineer performing a code review.
#
#                 Analyze the following repository code and return ONLY a valid JSON object.
#                 Don't include any reasoning.
#                 No markdown, no explanation, no code fences. Just the raw JSON.
#
#                 Return this exact structure:
#                 {{
#                   "summary": "2-3 sentence overview of what this repo does",
#                   "quality_score": <integer 1-10>,
#                   "tech_stack": ["list", "of", "languages", "frameworks", "libraries"],
#                   "strengths": ["strength 1", "strength 2", "strength 3"],
#                   "weaknesses": ["weakness 1", "weakness 2", "weakness 3"]
#                 }}
#
#                 Repository code:
#                 {code}
#                 """
#
#     payload = {
#         "model": "qwen/qwen3-32b",
#         "messages": [
#             {
#                 "role": "user",
#                 "content": prompt
#             }
#         ],
#         "temperature": 0.3
#     }
#
#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             url,
#             headers=headers,
#             json=payload,
#             timeout=60
#         )
#
#     response.raise_for_status()
#
#     data = response.json()
#     content = data['choices'][0]['message']['content']
#
#     # remove think block
#     cleaned = re.sub(
#         r"<think>.*?</think>",
#         "",
#         content,
#         flags=re.DOTALL
#     ).strip()
#
#     # convert returned JSON string -> python dictionary
#     parsed_response = json.loads(cleaned)
#
#     return parsed_response




GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


async def groq_post(payload: dict, retries: int = 4) -> str:
    """POST to Groq with exponential backoff on 429."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
    }
    for attempt in range(retries):
        async with httpx.AsyncClient() as client:
            response = await client.post(GROQ_URL, headers=headers, json=payload, timeout=60)

        if response.status_code == 429:
            wait = 2 ** attempt
            print(f"[groq_post] 429 — retrying in {wait}s (attempt {attempt + 1}/{retries})")
            await asyncio.sleep(wait)
            continue

        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    raise Exception("Groq rate limit exceeded after all retries.")


async def analyze_chunk(chunk: str, chunk_num: int, total_chunks: int) -> str:
    """
    Analyze a single chunk and return plain-text observations.
    Not final JSON — just structured notes for the synthesis step.
    """
    payload = {
        "model": MODEL,
        "temperature": 0.3,
        "messages": [{
            "role": "user",
            "content": (
                f"You are a senior software engineer doing a code review.\n"
                f"This is part {chunk_num} of {total_chunks} of a repository.\n\n"
                f"Extract observations ONLY — do NOT produce final output yet.\n"
                f"Return a short bullet-point list (plain text) covering:\n"
                f"- Languages / frameworks / libraries spotted\n"
                f"- Notable strengths\n"
                f"- Notable weaknesses or issues\n"
                f"- What this code appears to be doing\n\n"
                f"Code:\n{chunk}"
            ),
        }],
    }
    print(f"[analyze_chunk] Observing chunk {chunk_num}/{total_chunks}...")
    return await groq_post(payload)


async def analyze_repository(chunk_observations: list[str]) -> dict:
    """
    Final synthesis across all chunk observations.
    Returns:
        {
          "summary": "",
          "quality_score": 7,
          "tech_stack": [],
          "strengths": [],
          "weaknesses": []
        }
    """
    combined = "\n\n".join(
        f"--- Observations from part {i + 1} ---\n{obs}"
        for i, obs in enumerate(chunk_observations)
    )

    prompt = (
        f"You are a senior software engineer performing a final code review.\n\n"
        f"Below are observations collected from each part of a repository:\n\n"
        f"{combined}\n\n"
        f"Using all observations above, return ONLY a valid JSON object.\n"
        f"No markdown, no explanation, no code fences, no reasoning. Just raw JSON.\n\n"
        f"Return this exact structure:\n"
        f'{{\n'
        f'  "summary": "2-3 sentence overview of what this repo does",\n'
        f'  "quality_score": <integer 1-10>,\n'
        f'  "tech_stack": ["list", "of", "languages", "frameworks", "libraries"],\n'
        f'  "strengths": ["strength 1", "strength 2", "strength 3"],\n'
        f'  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"]\n'
        f'}}'
    )

    payload = {
        "model": MODEL,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}],
    }

    print(f"[analyze_repository] Final synthesis across {len(chunk_observations)} chunk(s)...")
    raw = await groq_post(payload)
    return json.loads(raw)