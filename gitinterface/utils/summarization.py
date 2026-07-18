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

            response.raise_for_status()
        if response.status_code == 429:
            wait = 2 ** attempt
            print(f"[groq_post] 429 — retrying in {wait}s (attempt {attempt + 1}/{retries})")
            await asyncio.sleep(wait)
            continue

        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    raise Exception("Groq rate limit exceeded after all retries.")


async def analyze_chunk(chunk: str, chunk_num: int, total_chunks: int,metadata: list[str]) -> str:
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
                f"You are a code analysis assistant reviewing part {chunk_num} of {total_chunks} of a repository.\n"
                f"Your job is to extract factual observations ONLY from this chunk.This is some extra data{metadata}\n"
                f"Do NOT make judgments. Do NOT say 'good' or 'bad'. Just report what you see.\n\n"
                f"Return plain text bullet points covering:\n"
                f"- What this code does (functional description, be specific)\n"
                f"- Languages, frameworks, libraries spotted\n"
                f"- Error handling: present, absent, or partial?\n"
                f"- Hardcoded values: credentials, magic numbers, config values baked in?\n"
                f"- Naming: descriptive or cryptic?\n"
                f"- Code structure: modular or monolithic?\n"
                f"- Dead code: commented-out blocks, unused imports, unreachable logic?\n"
                f"- Security signals: exposed secrets, unvalidated inputs, unsafe patterns?\n"
                f"- Anything else notable in this chunk\n\n"
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
        f"Below are observations collected from each part of this repository:\n\n"
        f"{combined}\n\n"
        f"Your job is to synthesize these observations into a final analysis.\n"
        f"Judge everything relative to the project's goal and complexity — not against an enterprise standard.\n\n"
        f"Use this rubric to determine good_practices and improvement_areas:\n"
        f"- Error handling: are failures caught or silently swallowed?\n"
        f"- Security: are secrets hardcoded, inputs unvalidated?\n"
        f"- Modularity: is logic broken into clear components or one giant block?\n"
        f"- Naming: are variables, functions, files descriptively named?\n"
        f"- Dead code: commented-out blocks, unused imports, leftover debug code?\n"
        f"- Dependency hygiene: are dependencies explicit and minimal?\n"
        f"- Documentation: is there a README, are complex parts explained?\n\n"
        f"quality_score rubric:\n"
        f"- 1-3: multiple rubric areas failing, hard to understand or run\n"
        f"- 4-6: some good practices, some gaps, functional but rough\n"
        f"- 7-8: most rubric areas satisfied, minor issues only\n"
        f"- 9-10: rubric fully satisfied, clean, well documented, production-ready\n\n"
        f"Return ONLY a valid JSON object. No markdown, no explanation, no code fences.\n\n"
        f"{{\n"
        f'  "summary": "2-3 sentence overview of what this repo does and who it is for",\n'
        f'  "tech_stack": ["languages", "frameworks", "libraries"],\n'
        f'  "quality_score": <integer 1-10>,\n'
        f'  "good_practices": ["only practices observed in the code, grounded in the rubric above"],\n'
        f'  "improvement_areas": ["specific issues observed, tied to rubric, relative to project goal"]\n'
        f"}}"
    )

    payload = {
        "model": MODEL,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}],
    }

    print(f"[analyze_repository] Final synthesis across {len(chunk_observations)} chunk(s)...")
    raw = await groq_post(payload)
    return json.loads(raw)