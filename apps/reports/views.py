from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .services import ReportService
from .serializers import TodaySummarySerializer, MonthlySummarySerializer
from apps.stores.models import Store


class TodaySummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(
                id=store_id,
                owner=request.user,
                is_deleted=False,
            )
        except Store.DoesNotExist:
            return Response({'detail': "Do'kon topilmadi."}, status=404)

        data = ReportService.today_summary(store)
        return Response(TodaySummarySerializer(data).data)


class MonthlySummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, store_id):
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            return Response(
                {'detail': 'year va month parametrlari kerak.'},
                status=400
            )

        try:
            store = Store.objects.get(
                id=store_id,
                owner=request.user,
                is_deleted=False,
            )
        except Store.DoesNotExist:
            return Response({'detail': "Do'kon topilmadi."}, status=404)

        data = ReportService.monthly_summary(store, int(year), int(month))
        return Response(MonthlySummarySerializer(data).data)
