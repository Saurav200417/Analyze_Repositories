import httpx
import requests
import base64
import asyncio

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from asgiref.sync import sync_to_async
from adrf.views import APIView

from gitinterface.utils.summarization import analyze_repository , analyze_chunk
from gitinterface.utils.embedding import create_embedding
from gitinterface.utils.extraction import clean_paths , extract_contents ,create_chunks
from gitinterface.models import User, Repo_Analysis, AbstractBaseModel

class RepositoryView(APIView):

    def get(self, request, username,repo_name=None):
        """
            API to get repository details
            if only username is provided then we will get all repos
            if reponame is given then only that repo will be returned
            if in params there is languages then language used is returned of a speccific repo
        """
        try:
            if not username:
                return Response({'message': 'username is required'}, status=HTTP_400_BAD_REQUEST)

            params = request.query_params.get("params")

            github_url = ""

            # CaSE 1 fetch all repos
            if not repo_name:
                github_url = f"https://api.github.com/users/{username}/repos"

            # CaSE 2 fetch repo languages
            elif params == "languages":
                github_url = (
                    f"https://api.github.com/repos/"
                    f"{username}/{repo_name}/languages"
                )

            # CaSE 3fetch specific repo
            else:
                github_url = (
                    f"https://api.github.com/repos/"
                    f"{username}/{repo_name}"
                )

            r = requests.get(github_url)
            data = {}
            if r.status_code == 200:
                data = r.json()
            return Response({"data":data},status=r.status_code)

        except Exception as e:
            return Response({'message': str(e)}, status=HTTP_400_BAD_REQUEST)

class RepositoryDetailView(APIView):
    """
        To fetch a specific file content or structure
        for repo structure pass branch name
    """
    def get(self, request, username, repo_name, tree_sha=None):
        try:
            if not username or not repo_name:
                return Response({'message': 'username or repo_name is required'}, status=HTTP_400_BAD_REQUEST)
            file = request.query_params.get("file")
            if not tree_sha:
                r = requests.get(f"https://api.github.com/repos/{username}/{repo_name}/contents/{file}")
            else :
                # https: // api.github.com / repos / Saurav200417 / EHR / git / trees / my - version
                r = requests.get(f"https://api.github.com/repos/{username}/{repo_name}/git/trees/{tree_sha}?recursive=1")
            data = {}
            if r.status_code == 200:
                data = r.json()
                if 'content' in data:
                    base64_content = base64.b64decode(data['content'])
                    # bytes -> normal string
                    decoded_text = base64_content.decode("utf-8")
                    data["decoded_content"] = decoded_text
                    result = analyze_repository(data["decoded_content"])
                    data['summary'] = result['summary']

            return Response({"data": data}, status=r.status_code)

        except Exception as e:
            return Response({'message': str(e)}, status=HTTP_400_BAD_REQUEST)

class RepositoryExtractView(APIView):
    async def get(self, request, username, repo_name, tree_sha=None):
        """
        API to extract every file content/code of a repo
        """
        try:
            user = await sync_to_async(User.objects.get)(email=request.user)
            if not user :
                return Response({'message': 'user not exist'}, status=HTTP_404_NOT_FOUND)
            if not username or not repo_name:
                return Response({'message': 'username or repo_name is required'}, status=HTTP_400_BAD_REQUEST)

            # First extract the tree structure
            # sync
            # response = requests.get(f"https://api.github.com/repos/{username}/{repo_name}/git/trees/{tree_sha}?recursive=1")
            # async
            sha_ref = tree_sha or "HEAD"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.github.com/repos/{username}/{repo_name}/git/trees/{sha_ref}?recursive=1"
                )
            results = response.json()
            if response.status_code == 200:
                repo_structure = response.json()
                sha = repo_structure['sha']
                tree = repo_structure['tree']
                # paths =  extract_path(tree)
                # No need for a separate function at all
                # 2 get every file path
                paths = [item['path'] for item in tree if item['type'] == 'blob']
                paths = clean_paths(paths)

                # 3 extract code/content from every file

                  #without chunk
                # contents = await extract_contents(paths, username, repo_name)
                # results = await analyze_repository(contents)

                  #with chunk
                contents = await extract_contents(paths, username, repo_name)
                chunks = create_chunks(contents)

                # Analyze each chunk sequentially (avoid 429s)
                chunk_observations = []
                for i, chunk in enumerate(chunks):
                    obs = await analyze_chunk(chunk, chunk_num=i + 1, total_chunks=len(chunks))
                    chunk_observations.append(obs)
                    if i < len(chunks) - 1:
                        await asyncio.sleep(1)  # rate limit breathing room
                # Final synthesis
                results = await analyze_repository(chunk_observations)
                obj, created = await sync_to_async(
                    Repo_Analysis.objects.update_or_create
                )(
                    user=user,
                    repo_name=repo_name,
                    defaults={
                        "content": results,
                        "tree_sha": sha,
                        "created_user":user,
                        "last_modified_user": user,
                    }
                )

                if created:
                    obj.created_user = user
                    await sync_to_async(obj.save)()
            return Response({"data":{"message": "repo successfully extracted","result":results}}, status=response.status_code)
        except Exception as e:
            return Response({'message': str(e)}, status=HTTP_400_BAD_REQUEST)

class EmbeddingView(APIView):
    async def post(self, request):
        try:
            # user
            user = await sync_to_async(User.objects.get)(email=request.user)

            repo_name = request.data.get('repo_name')
            if not repo_name:
                return Response(
                    {'message': 'repo_name is required'},
                    status=HTTP_400_BAD_REQUEST
                )

            # repo analysis object for this user repo
            try:
                obj = await sync_to_async(Repo_Analysis.objects.get)(
                    user=user,
                    repo_name=repo_name
                )
            except Repo_Analysis.DoesNotExist:
                return Response(
                    {'message': 'No analysis found for this repo'},
                    status=HTTP_404_NOT_FOUND
                )

            # content
            content = obj.content
            if not content:
                return Response(
                    {'message': 'No content found for this repo'},
                    status=HTTP_404_NOT_FOUND
                )

            # embedding
            embedding = await create_embedding(content)

            # Save embedding back to the object
            obj.embedding = embedding
            await sync_to_async(obj.save)(update_fields=['embedding'])

            return Response({'message': 'Embedding created successfully'}, status=HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'message': 'User not found'}, status=HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'message': str(e)}, status=HTTP_400_BAD_REQUEST)