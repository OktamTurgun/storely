from rest_framework import generics, permissions
from .models import Store
from .serializers import StoreSerializer, StoreListSerializer


class StoreListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return StoreListSerializer
        return StoreSerializer

    def get_queryset(self):
        return Store.objects.filter(
            owner=self.request.user,
            is_deleted=False,
        ).order_by('-created_at')


class StoreDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StoreSerializer

    def get_queryset(self):
        return Store.objects.filter(
            owner=self.request.user,
            is_deleted=False,
        )

    def perform_destroy(self, instance):
        instance.delete()
