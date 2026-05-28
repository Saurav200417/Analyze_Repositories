from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from gitinterface.view.chat import ChatView
from gitinterface.view.repositories import RepositoryView,RepositoryDetailView,RepositoryExtractView,EmbeddingView
from gitinterface.view.authentication import LoginView , RegisterView
urlpatterns = {
    # login
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    # Get all repos
    path('users/<str:username>/repos/', RepositoryView.as_view()),
    # Get a specific repo
    path('users/<str:username>/<str:repo_name>/', RepositoryView.as_view()),
    # Get structure of a repo so that later we can access a file
    path('users/<str:username>/<str:repo_name>/trees/<str:tree_sha>/', RepositoryDetailView.as_view()),
    # Get contents of specific file
    path('users/<str:username>/<str:repo_name>/contents/', RepositoryDetailView.as_view()),
    # retrieve contents from all files of a repo
    path('extract/<str:username>/<str:repo_name>/<str:tree_sha>/',RepositoryExtractView.as_view()),
    # create embedding and store it in db
    path('embeddings/',EmbeddingView.as_view()),
    # chat api
    path('chat/',ChatView.as_view()),
}
urlpatterns = format_suffix_patterns(urlpatterns)

