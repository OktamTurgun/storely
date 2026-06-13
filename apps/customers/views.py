from rest_framework import generics, permissions
from .models import Customer
from .serializers import CustomerSerializer, CustomerListSerializer


class CustomerListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CustomerListSerializer
        return CustomerSerializer

    def get_queryset(self):
        store_id = self.kwargs['store_id']
        return Customer.objects.filter(
            store__owner=self.request.user,
            store_id=store_id,
            is_deleted=False,
        ).order_by('name')


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CustomerSerializer

    def get_queryset(self):
        return Customer.objects.filter(
            store__owner=self.request.user,
            is_deleted=False,
        )

    def perform_destroy(self, instance):
        instance.delete()
