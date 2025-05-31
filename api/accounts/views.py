import logging
from rest_framework.decorators import api_view, permission_classes # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny, IsAuthenticated # type: ignore
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework import status # type: ignore
from django.shortcuts import render
from .models import User
from .utils import generate_jwt_tokens

