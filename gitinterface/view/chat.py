import httpx
import numpy as np

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND ,HTTP_500_INTERNAL_SERVER_ERROR
from asgiref.sync import sync_to_async
from adrf.views import APIView

from gitinterface.models import Repo_Analysis ,User,Chat,Messages
# from gitinterface.tasks import generate_answer_task, create_embedding_task
from gitinterface.utils.embedding import create_embedding
from gitinterface.utils.chat import generate_answer
from gitinterface.utils.choices import ROLE_CHOICES

# class ChatView(APIView):
#     async def post(self, request, *args, **kwargs):
#         try:
#             question = request.data.get('question')
#             if not question:
#                 return Response({"error": "Question is required"}, status=HTTP_400_BAD_REQUEST)
#
#             user = request.user  # This is the authenticated user object
#             chat_name = request.data.get('chat_name')
#
#             # Fix 1: Use filter().first() instead of get() to avoid DoesNotExist exception
#             # and to avoid shadowing the User model import with a variable named 'user'
#             user_obj = await sync_to_async(
#                 lambda: User.objects.filter(email=user).first()
#             )()
#             if not user_obj:
#                 return Response({"error": "User not found"}, status=HTTP_404_NOT_FOUND)
#             print("user",user_obj)
#             if not chat_name:
#                 return Response({"error": "Chat name is required"}, status=HTTP_400_BAD_REQUEST)
#
#             # Fix 2: Use filter().first() instead of get() to avoid DoesNotExist,
#             # since get() raises an exception when no object is found rather than returning None
#             chat_obj = await sync_to_async(
#                 lambda: Chat.objects.filter(name=chat_name, user=user_obj,created_user=user_obj,last_modified_user=user_obj).first()
#             )()
#             # print("chat",chat_obj)
#             # if not chat_obj:
#             #     chat_obj = await sync_to_async(
#             #         lambda: Chat.objects.create(name=chat_name, user=user_obj,created_user=user_obj,last_modified_user=user_obj)
#             #     )()
#             # print("chat",chat_obj)
#             # Fix 3: get_or_create returns a tuple (instance, created_bool), so unpack it.
#             # Also provide all required fields: role, content, sequence.
#             # We create/get the "seed" user message placeholder for this chat session.
#             message_obj, created = await sync_to_async(
#                 lambda: Messages.objects.get_or_create(
#                     chat=chat_obj,
#                     role='user',
#                     defaults={
#                         # 'content': question,
#                         'sequence': 1,
#                         'created_user':user_obj,
#                         'last_modified_user':user_obj,
#                     }
#                 )
#             )()
#
#             # Fix 4: Use filter() not get() — a user can have multiple repos.
#             # Wrap lambda correctly with sync_to_async and call the result.
#             repo_names = await sync_to_async(
#                 lambda: list(Repo_Analysis.objects.filter(user=user_obj))
#             )()
#             if not repo_names:
#                 return Response({"error": "No repositories found"}, status=HTTP_404_NOT_FOUND)
#
#             # Fetch all stored repo embeddings (content + embedding pairs) for similarity search
#             stored = await sync_to_async(
#                 lambda: list(
#                     Repo_Analysis.objects.filter(user=user_obj).values_list('content', 'embedding')
#                 )
#             )()
#
#             # Fix 5: Keep consistent tuple shape (content, embedding) when appending chat
#             # message embeddings so cosine_similarity doesn't break on x[1] below.
#             # Previous code appended raw (embedding,) tuples, mismatching the (content, embedding) shape.
#             chat_history = None
#             if chat_obj:
#                 # Get chat history — both questions and answers in order
#                 chat_history = await sync_to_async(
#                     lambda: list(
#                         Messages.objects.filter(chat=chat_obj)
#                         .order_by('sequence')
#                         .values_list('role', 'content')  # [('user', '...'), ('assistant', '...')]
#                     )
#                 )()
#                 # stored.extend(chat_messages)  # extend, not append, to flatten into the list
#                 # Instead lets fetch previous latest answer
#             # Cosine similarity only against repo embeddings
#             question_embedding = await create_embedding(question, input_type="search_query")
#             def cosine_similarity(a, b):
#                 a, b = np.array(a), np.array(b)
#                 return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
#             ranked = sorted(
#                 stored,
#                 key=lambda x: cosine_similarity(question_embedding, x[1]),
#                 reverse=True
#             )
#             top_context = [summary for summary, _ in ranked[:3]]
#
#             answer = await generate_answer(question, top_context, chat_history)
#             answer_embedding = await create_embedding(answer, input_type="search_query")
#
#             # Save question and answer as separate messages
#             last_seq = await sync_to_async(
#                 lambda: Messages.objects.filter(chat=chat_obj).count()
#             )()
#
#             # Save user question
#             await sync_to_async(
#                 lambda: Messages.objects.create(
#                     chat=chat_obj,
#                     role='user',
#                     content=question,
#                     embedding=question_embedding,
#                     sequence=last_seq + 1,
#                     created_user=user_obj,
#                     last_modified_user=user_obj,
#                 )
#             )()
#
#             # Save assistant answer
#             await sync_to_async(
#                 lambda: Messages.objects.create(
#                     chat=chat_obj,
#                     role='assistant',
#                     content=answer,
#                     embedding=answer_embedding,
#                     sequence=last_seq + 2,
#                     created_user=user_obj,
#                     last_modified_user=user_obj,
#                 )
#             )()
#             # question_embedding = await create_embedding(question, input_type="search_query")
#             #
#             #
#             # ranked = sorted(
#             #     stored,
#             #     key=lambda x: cosine_similarity(question_embedding, x[1]),
#             #     reverse=True
#             # )
#             #
#             # top_context = [summary for summary, _ in ranked[:3]]
#             #
#             # # Fix 6: generate_answer is async — must be awaited
#             # answer = await generate_answer(question, top_context,chat_answer)
#             # answer_embedding = await create_embedding(answer, input_type="search_query")
#             # # Fix 7: Save the new user message with its embedding.
#             # # message_obj is a model INSTANCE — never call .objects on an instance.
#             # # Use instance attribute assignment + async save() instead.
#             # if created:
#             #     # Already created with content=question above; just add the embedding
#             #     message_obj.embedding = answer_embedding
#             #     message_obj.content = answer
#             #     await sync_to_async(lambda: message_obj.save())()
#             #     # await sync_to_async(message_obj.save)()
#             # else:
#             #     # Create a new message for this question in the existing chat
#             #     last_seq = await sync_to_async(
#             #         lambda: Messages.objects.filter(chat=chat_obj).count()
#             #     )()
#             #     await sync_to_async(
#             #         lambda: Messages.objects.create(
#             #             chat=chat_obj,
#             #             role='user',
#             #             content=answer,
#             #             embedding=answer_embedding,
#             #             sequence=last_seq + 1,
#             #         )
#             #     )()
#
#             return Response({"answer": answer}, status=HTTP_200_OK)
#
#         except User.DoesNotExist:
#             return Response({"error": "User not found"}, status=HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


class ChatView(APIView):
    async def post(self, request, *args, **kwargs):
        try:
            question = request.data.get('question')
            if not question:
                return Response({"error": "Question is required"}, status=HTTP_400_BAD_REQUEST)

            user = request.user
            chat_name = request.data.get('chat_name')

            if not chat_name:
                return Response({"error": "Chat name is required"}, status=HTTP_400_BAD_REQUEST)

            user_obj = await sync_to_async(
                lambda: User.objects.filter(email=user).first()
            )()
            if not user_obj:
                return Response({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

            # Find existing chat or create new one for this user
            chat_obj = await sync_to_async(
                lambda: Chat.objects.filter(name=chat_name, user=user_obj).first()
            )()
            if not chat_obj:
                # First time — create the chat
                chat_obj = await sync_to_async(
                    lambda: Chat.objects.create(
                        name=chat_name,
                        user=user_obj,
                        created_user=user_obj,
                        last_modified_user=user_obj
                    )
                )()

            # Fetch chat history — empty list on first message, populated on subsequent ones
            chat_history = await sync_to_async(
                lambda: list(
                    Messages.objects.filter(chat=chat_obj)
                    .order_by('sequence')
                    .values_list('role', 'content')
                )
            )()
            # chat_history = [] on first question, [('user', ...), ('assistant', ...)] on subsequent ones

            # Fetch repo embeddings for RAG
            repo_names = await sync_to_async(
                lambda: list(Repo_Analysis.objects.filter(user=user_obj))
            )()
            if not repo_names:
                return Response({"error": "No repositories found"}, status=HTTP_404_NOT_FOUND)

            stored = await sync_to_async(
                lambda: list(
                    Repo_Analysis.objects.filter(user=user_obj).values_list('content', 'embedding')
                )
            )()

            question_embedding = await create_embedding(question, input_type="search_query")

            def cosine_similarity(a, b):
                a, b = np.array(a), np.array(b)
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

            ranked = sorted(
                stored,
                key=lambda x: cosine_similarity(question_embedding, x[1]),
                reverse=True
            )
            top_context = [summary for summary, _ in ranked[:3]]

            answer = await generate_answer(question, top_context, chat_history)
            answer_embedding = await create_embedding(answer, input_type="search_query")

            # Get current max sequence to append after
            last_seq = await sync_to_async(
                lambda: Messages.objects.filter(chat=chat_obj).count()
            )()

            # Save user question
            await sync_to_async(
                lambda: Messages.objects.create(
                    chat=chat_obj,
                    role='user',
                    content=question,
                    embedding=question_embedding,
                    sequence=last_seq + 1,
                    created_user=user_obj,
                    last_modified_user=user_obj,
                )
            )()

            # Save assistant answer
            await sync_to_async(
                lambda: Messages.objects.create(
                    chat=chat_obj,
                    role='assistant',
                    content=answer,
                    embedding=answer_embedding,
                    sequence=last_seq + 2,
                    created_user=user_obj,
                    last_modified_user=user_obj,
                )
            )()

            return Response({"answer": answer}, status=HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)