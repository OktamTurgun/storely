from rest_framework.permissions import BasePermission


class IsStoreOwner(BasePermission):
    message = "Bu do'konga kirishga ruxsatingiz yo'q."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        store_id = view.kwargs.get('store_id')
        if not store_id:
            return True

        # Import shu yerda — circular import ham bo'lmaydi
        from apps.stores.models import Store

        return Store.objects.filter(
            id=store_id,
            owner=request.user,
            is_deleted=False,
        ).exists()


class IsObjectOwner(BasePermission):
    message = "Bu obyektga kirishga ruxsatingiz yo'q."

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'store'):
            return obj.store.owner == request.user
        return False