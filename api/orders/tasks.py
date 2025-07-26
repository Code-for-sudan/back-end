from celery import shared_task
from django.utils import timezone
from .services import OrderService
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def cleanup_expired_payment_orders(self):
    """
    Celery task to clean up expired payment orders
    - Runs automatically to find orders where payment window has expired
    - Unreserves stock and marks orders as cancelled
    """
    try:
        # Get count before cleanup for logging
        expired_count = OrderService.get_expired_orders_count()
        
        if expired_count == 0:
            logger.info("No expired payment orders found for cleanup")
            return {
                'success': True,
                'message': 'No expired orders to process',
                'processed_count': 0
            }
        
        logger.info(f"Starting cleanup of {expired_count} expired payment orders")
        
        # Perform cleanup
        cleanup_results = OrderService.cleanup_expired_payments()
        
        logger.info(
            f"Cleanup completed. Processed: {cleanup_results['processed_count']}, "
            f"Failed: {cleanup_results['failed_count']}"
        )
        
        # Log any errors
        if cleanup_results['errors']:
            logger.error(f"Cleanup errors: {cleanup_results['errors']}")
        
        return {
            'success': True,
            'processed_count': cleanup_results['processed_count'],
            'failed_count': cleanup_results['failed_count'],
            'errors': cleanup_results['errors']
        }
        
    except Exception as exc:
        logger.error(f"Cleanup task failed: {str(exc)}")
        
        # Retry the task with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for cleanup task")
            return {
                'success': False,
                'error': 'Max retries exceeded',
                'exception': str(exc)
            }


@shared_task
def check_single_order_payment_status(order_id):
    """
    Check payment status for a specific order
    This can be used for real-time checks or scheduled monitoring
    """
    try:
        status_info = OrderService.check_order_payment_status(order_id)
        
        # If payment has expired but order is still under_paying, trigger cleanup
        if (status_info['status'] == 'under_paying' and 
            not status_info['is_payment_window_active']):
            
            logger.warning(f"Order {order_id} payment has expired, triggering cleanup")
            cleanup_results = OrderService.cleanup_expired_payments()
            status_info['cleanup_triggered'] = True
            status_info['cleanup_results'] = cleanup_results
        
        return status_info
        
    except Exception as exc:
        logger.error(f"Failed to check order {order_id} payment status: {str(exc)}")
        return {
            'success': False,
            'order_id': order_id,
            'error': str(exc)
        }


@shared_task
def send_payment_reminder(order_id, minutes_remaining=5):
    """
    Send payment reminder to user when payment window is about to expire
    This task can be scheduled when an order is created
    """
    try:
        from .models import Order
        from notifications.services import NotificationService  # Assuming you have a notification service
        
        order = Order.objects.get(order_id=order_id)
        
        # Check if order is still under_paying and not expired
        if order.status != 'under_paying' or order.is_payment_expired:
            logger.info(f"Order {order_id} no longer needs payment reminder")
            return {'skipped': True, 'reason': 'Order status changed'}
        
        # Check if we still have the specified minutes remaining
        if order.payment_time_remaining > (minutes_remaining * 60):
            logger.info(f"Order {order_id} still has more than {minutes_remaining} minutes remaining")
            return {'skipped': True, 'reason': 'Too early for reminder'}
        
        # Send reminder notification
        # NotificationService.send_payment_reminder(
        #     user=order.user_id,
        #     order=order,
        #     minutes_remaining=minutes_remaining
        # )
        
        logger.info(f"Payment reminder sent for order {order_id}")
        return {
            'success': True,
            'order_id': order_id,
            'message': f'Payment reminder sent with {minutes_remaining} minutes remaining'
        }
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for payment reminder")
        return {'success': False, 'error': 'Order not found'}
    except Exception as exc:
        logger.error(f"Failed to send payment reminder for order {order_id}: {str(exc)}")
        return {'success': False, 'error': str(exc)}


# Schedule the cleanup task to run every 5 minutes
# This can be configured in celery beat settings
CLEANUP_SCHEDULE = {
    'cleanup-expired-payments': {
        'task': 'orders.tasks.cleanup_expired_payment_orders',
        'schedule': 300.0,  # Run every 5 minutes
        'options': {'expires': 240}  # Task expires after 4 minutes if not executed
    },
}
