# import cohere
#
#
# async def create_embedding(string):
#
#     co = cohere.ClientV2()
#
#     text_inputs = [
#         {
#             "content": [
#                 {"type": "text", "text": "hello"},
#                 {"type": "text", "text": "goodbye"}
#             ]
#         },
#     ]
#     async with httpx.AsyncClient() as client:
#
#         response = co.embed(
#             inputs=text_inputs,
#             model="embed-v4.0",
#             input_type="classification",
#             embedding_types=["float"],
#         )
#     return response

import cohere
import asyncio
from functools import partial
from django.conf import settings

async def create_embedding(text: str,input_type: str = "search_document") -> list[float]:
    """
    Create a float embedding for a single string using Cohere embed-v4.0.
    Returns a flat list of floats.
    """
    co = cohere.ClientV2(settings.COHERE_API_KEY)

    # Run the synchronous Cohere call in a thread pool to keep it non-blocking
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        partial(
            co.embed,
            inputs=[{"content": [{"type": "text", "text": text}]}],
            model="embed-v4.0",
            input_type=input_type,   # use search_query for query-side embeddings
            embedding_types=["float"],
        )
    )

    return response.embeddings.float[0]   # flat list[float] for the first (only) input