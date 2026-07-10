from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import DashboardSummarySerializer
from .services import build_dashboard_summary


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: DashboardSummarySerializer})
    def get(self, request):
        summary = build_dashboard_summary(user=request.user)
        serializer = DashboardSummarySerializer(summary.__dict__)
        return Response(serializer.data)
