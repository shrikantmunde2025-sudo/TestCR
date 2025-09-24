from django.conf import settings
from django.core.cache import cache

from rest_framework import response as drf_response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from dbz_shared.auth.restframework import JWTTokenAuthentication

from common.utils import send_email_to_user
from core import constants as core_constants
from core.authentication import ProxyUserJWTAuthentication
from core.models import User
from core.users.constants import AGENT_ACCOUNTS_CACHE_KEY_PREFIX
from core.users.models import Agent
from core.users.models import UserProxyAccess
from core.users.permissions import ProxyUserViewPermission
from seller_service.api.v1.agent.serializers import AccountResponseSerializer
from seller_service.api.v1.agent.serializers import AccountsQueryParamsSerializer
from seller_service.api.v1.agent.serializers import CacheableAccountResponseSerializer
from seller_service.api.v1.agent.serializers import InformationParamSerializer
from seller_service.api.v1.agent.serializers import InformationSerializer
from seller_service.api.v1.listings.permissions import PAAIsAuthenticatedPermission
from seller_service.recommendations.service import RecommendationGenerationError
from seller_service.recommendations.service import RecommendationService


class AgentLeadListCreateView(APIView):

    authentication_classes = (JWTTokenAuthentication,)
    permission_classes = (PAAIsAuthenticatedPermission,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = settings.PAA_AGENT_LEAD

    def _get_user_details(self, user_id: int) -> User:
        """
        Get user details from database.
        Raises ValidationError if user not found.
        """
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist as exc:
            raise ValidationError('User not found') from exc

    def _send_notification(self, user: User, category_name: str) -> None:
        """
        Send email notification to the ops team about a new agent lead.
        """
        full_name = f'{user.first_name} {user.last_name}'.strip()
        phone = user.phone if user.is_phone_verified else ''

        send_email_to_user(
            recipients=[settings.AGENT_LEAD_NOTIFICATION_RECIPIENT],
            template_name='property-agent-chooses-paa',
            template_vars={
                'user_name': full_name,
                'user_email': user.email,
                'user_phone_number': phone,
                'category_name': category_name,
            },
            user_id=user.user_id,
            subject='New Agent Lead Registration',
            tags=['agent-lead'],
        )

    def post(self, request: Request) -> Response:
        """
        Handle POST request to create agent lead and send notification.
        Returns 201 on success with confirmation message.
        """
        try:
            user = self._get_user_details(request.user.id)
            data = request.data

            category_name = data.get('category_name', '').strip()

            self._send_notification(user, category_name)

            return Response(
                {'message': 'Lead created successfully'},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AgentInformation(APIView):
    authentication_classes = (ProxyUserJWTAuthentication,)
    permission_classes = (ProxyUserViewPermission,)

    def get(self, request: Request) -> Response:
        params = InformationParamSerializer(data=dict(request.query_params))
        params.is_valid(raise_exception=True)
        user = request.selected_user
        agents = Agent.objects.filter(user=user, **params.data)
        if not agents:
            raise ValidationError('Agent not found')
        serializer = InformationSerializer(
            agents,
        )
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class AgentRecommendationsView(APIView):
    authentication_classes = (ProxyUserJWTAuthentication,)
    permission_classes = (ProxyUserViewPermission,)

    def handle_exception(self, exc: Exception) -> drf_response.Response:
        """Handle RecommendationGenerationError and let DRF handle other exceptions."""
        if isinstance(exc, RecommendationGenerationError):
            return Response(
                {'error': 'Failed to generate recommendations'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(exc, Agent.DoesNotExist):
            return Response(
                {'detail': 'No agent associated with this user'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().handle_exception(exc)

    def get(self, request, *args, **kwargs):

        user = request.selected_user
        agent = Agent.get_listing_management_enabled_agent(
            user=user,
            category_slugs=[
                core_constants.USED_CARS_SLUG,
                core_constants.RENTAL_CARS_SLUG,
            ],
        )
        if not agent:
            raise Agent.DoesNotExist('No agent associated with this user')
        recommendations = RecommendationService.get_or_cache_agent_recommendations(agent)
        return Response(
            {
                'success': True,
                'result': recommendations,
            },
        )


class AgentAccountsListView(ListAPIView):
    """API view for retrieving agent accounts accessible to a proxy user."""

    CACHE_KEY_PREFIX = AGENT_ACCOUNTS_CACHE_KEY_PREFIX

    authentication_classes = (ProxyUserJWTAuthentication,)
    permission_classes = (ProxyUserViewPermission,)
    serializer_class = AccountResponseSerializer

    def handle_exception(self, exc):
        if isinstance(exc, ValidationError):
            return Response(
                {'success': False, 'errors': exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().handle_exception(exc)

    def _validate_and_get_search_term(self):
        serializer = AccountsQueryParamsSerializer(data=self.request.query_params)
        if not serializer.is_valid(raise_exception=True):
            raise ValidationError(serializer.errors)
        return serializer.validated_data.get('search_term', '').strip()

    def get_queryset(self):
        return UserProxyAccess.get_accessible_agents_for_user(
            self.request.selected_user,
        )

    def list(self, request, *args, **kwargs):
        search_term = self._validate_and_get_search_term()

        # Check cache for full agent list (language-agnostic)
        cache_key = f'{self.CACHE_KEY_PREFIX}:{request.selected_user.id}'
        cached_data = cache.get(cache_key)

        if cached_data:
            # Use cached language-agnostic data
            full_payload_raw = cached_data['payload']
        else:
            # Generate language-agnostic response and cache it
            queryset = self.get_queryset()
            cacheable_serializer = CacheableAccountResponseSerializer(queryset, many=True)
            full_payload_raw = cacheable_serializer.data

            # Cache language-agnostic data for 2 hours
            cache_data = {'payload': full_payload_raw, 'total_size': len(full_payload_raw)}
            cache.set(cache_key, cache_data, timeout=7200)

        # Apply language selection to cached data
        response_serializer = AccountResponseSerializer(full_payload_raw, many=True)
        full_payload = response_serializer.data

        # Apply search filter if provided
        if search_term:
            filtered_payload = [
                agent for agent in full_payload
                if search_term.lower() in (agent.get('agent_name', '') or '').lower()
            ]
        else:
            filtered_payload = full_payload

        response_data = {'payload': filtered_payload, 'total_size': len(filtered_payload)}
        return Response(response_data, status=status.HTTP_200_OK)