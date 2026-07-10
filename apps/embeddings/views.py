from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.exceptions import AIProviderError

from .serializers import (
    SemanticSearchRequestSerializer,
    SemanticSearchResponseSerializer,
)
from .services import semantic_search


class SemanticSearchView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SemanticSearchRequestSerializer,
        responses={200: SemanticSearchResponseSerializer},
    )
    def post(self, request):
        serializer = SemanticSearchRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        organization = serializer.validated_data["organization"]
        query = serializer.validated_data["query"]
        limit = serializer.validated_data["limit"]

        try:
            results = semantic_search(organization=organization, query=query, limit=limit)
        except AIProviderError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_serializer = SemanticSearchResponseSerializer(
            {
                "query": query,
                "results": [result.__dict__ for result in results],
            }
        )
        return Response(response_serializer.data)
