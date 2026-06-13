from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from .models import Debt
from .serializers import DebtSerializer, DebtPaySerializer
from .services import DebtService


class DebtListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DebtSerializer

    def get_queryset(self):
        store_id = self.kwargs['store_id']
        closed = self.request.query_params.get('closed', 'false') == 'true'
        return DebtService.get_store_debts(
            store_id=store_id,
            closed=closed,
        ).filter(store__owner=self.request.user)


class DebtPayView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            debt = Debt.objects.get(
                id=pk,
                store__owner=request.user,
                is_deleted=False,
            )
        except Debt.DoesNotExist:
            return Response({'detail': 'Qarz topilmadi.'}, status=404)

        serializer = DebtPaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = DebtService.pay_debt(
                debt,
                serializer.validated_data['amount']
            )
        except ValidationError as e:
            return Response({'detail': str(e.message)}, status=400)

        return Response(DebtSerializer(updated).data)
