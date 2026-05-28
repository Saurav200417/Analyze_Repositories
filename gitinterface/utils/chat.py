import asyncio
from functools import partial
from groq import Groq
from django.conf import settings

from gitinterface.utils.summarization import groq_post

# async def generate_answer(question: str, context: list[str],chat_answer=None) -> str:
#     """
#     Generate an answer using Groq's model given a question
#     and retrieved repository context.
#     """
#
#     print("Generating answer")
#
#     formatted_context = "\n\n".join(
#         f"Repo {i+1}:\n{snippet}"
#         for i, snippet in enumerate(context)
#     )
#
#     system_prompt = (
#         "You are an expert code assistant. "
#         "You are given summaries of relevant repositories as context. "
#         "Use them to answer the user's question accurately and concisely."
#     )
#
#     user_prompt = (
#         f"Context:\n{formatted_context}\n\n"
#         f"Context:\n{chat_answer}\n\n"
#         f"Question: {question}"
#     )
#
#     payload = {
#         "model": "llama-3.3-70b-versatile",
#         "messages": [
#             {
#                 "role": "system",
#                 "content": system_prompt
#             },
#             {
#                 "role": "user",
#                 "content": user_prompt
#             }
#         ],
#         "temperature": 0.2,
#         "max_tokens": 500,
#     }
#
#     print("Before Groq API call")
#
#     answer = await groq_post(payload)
#
#     return answer

async def generate_answer(question: str, context: list[str], chat_history=None) -> str:
    formatted_context = "\n\n".join(
        f"Repo {i+1}:\n{snippet}"
        for i, snippet in enumerate(context)
    )

    system_prompt = (
        "You are an expert code assistant. "
        "You are given summaries of relevant repositories as context. "
        "Use them to answer the user's question accurately and concisely."
    )

    # Build messages list with history
    messages = [{"role": "system", "content": system_prompt}]

    # Inject previous conversation turns so LLM has memory
    if chat_history:
        for role, content in chat_history:  # [('user', '...'), ('assistant', '...')]
            messages.append({"role": role, "content": content})

    # Add current question with repo context
    messages.append({
        "role": "user",
        "content": f"Context:\n{formatted_context}\n\nQuestion: {question}"
    })

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 500,
    }

    return await groq_post(payload)