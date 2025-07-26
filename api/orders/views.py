from django.shortcuts import render

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from .services import OrderService
from .models import Order
from .tasks import cleanup_expired_payment_orders, check_single_order_payment_status
import logging

logger = logging.getLogger(__name__)


class OrderPaymentStatusView(APIView):
    """Check payment status and remaining time for an order"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, order_id):
        try:
            # Verify user owns this order or is admin
            order = Order.objects.get(order_id=order_id)
            if order.user_id != request.user and not request.user.is_staff:
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            payment_status = OrderService.check_order_payment_status(order_id)
            return Response(payment_status, status=status.HTTP_200_OK)
            
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ManualCleanupExpiredOrdersView(APIView):
    """Manually trigger cleanup of expired payment orders (Admin only)"""
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        try:
            # Trigger manual cleanup
            cleanup_results = OrderService.cleanup_expired_payments()
            
            return Response({
                'message': 'Cleanup completed successfully',
                'results': cleanup_results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ExpiredOrdersCountView(APIView):
    """Get count of orders that need cleanup (Admin only)"""
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        try:
            expired_count = OrderService.get_expired_orders_count()
            return Response({
                'expired_orders_count': expired_count,
                'needs_cleanup': expired_count > 0
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def trigger_cleanup_task(request):
    """Trigger the Celery cleanup task manually"""
    try:
        # Start the cleanup task asynchronously
        task = cleanup_expired_payment_orders.delay()
        
        return Response({
            'message': 'Cleanup task started',
            'task_id': task.id,
            'status': 'running'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_my_order_payment(request, order_id):
    """Check payment status for user's own order"""
    try:
        # Verify user owns this order
        order = Order.objects.get(order_id=order_id, user_id=request.user)
        
        # Trigger async check
        task = check_single_order_payment_status.delay(order_id)
        
        # Also get immediate status
        immediate_status = OrderService.check_order_payment_status(order_id)
        
        return Response({
            'immediate_status': immediate_status,
            'async_check_task_id': task.id
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
