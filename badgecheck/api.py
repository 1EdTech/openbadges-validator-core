from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from badgecheck.api_serializers import IntegritySerializer


class VerifyBadgeInstanceView(APIView):
    permission_classes = (permissions.AllowAny,)
    """
    Endpoint for posting badge information to verify. Returns JSON serialization of the results.
    """
    def post(self, request):
        """
        POST badge information to retrieve integrity verification information. 
        The recipient parameter is required, along with either a badge image file, hosted
        badge assertion URL, or badge assertion content itself.
        ---
        serializer: IntegritySerializer
        parameters:
            - name: recipient
              description: The identifier of the badge recipient. Verification information will only be returned if this is correct.
              required: true
              type: string
              paramType: form
            - name: image
              description: A baked badge image file
              required: false
              type: file
              paramType: form
            - name: url
              description: The URL of a hosted badge assertion
              required: false
              type: string
              paramType: form
            - name: assertion
              description: The signed or hosted assertion content, either as a JSON string or base64-encoded JWT
              required: false
              type: string
              paramType: form
        """
        serializer = IntegritySerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        # if serializer.instance.version is None:
        #     return Response()

        return Response(serializer.data)
