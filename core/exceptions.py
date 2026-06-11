from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, ValidationError):
        return Response(
            {'detail': exc.message if hasattr(exc, 'message') else str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )

    if response is not None:
        response.data = {
            'detail': response.data if isinstance(response.data, str)
                      else response.data.get('detail', response.data)
        }

    return response