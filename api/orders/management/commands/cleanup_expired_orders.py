from django.core.management.base import BaseCommand
from django.utils import timezone
from orders.services import OrderService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up expired payment orders and unreserve their stock'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about the cleanup process',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting expired payment orders cleanup...')
        )

        try:
            # Check how many orders need cleanup
            expired_count = OrderService.get_expired_orders_count()
            
            if expired_count == 0:
                self.stdout.write(
                    self.style.SUCCESS('No expired payment orders found.')
                )
                return

            self.stdout.write(
                f'Found {expired_count} expired payment orders to process.'
            )

            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('DRY RUN MODE - No changes will be made')
                )
                
                # In dry run, just show which orders would be affected
                from orders.models import Order
                expired_orders = Order.objects.filter(
                    status='under_paying',
                    payment_expires_at__lt=timezone.now()
                )
                
                for order in expired_orders:
                    self.stdout.write(
                        f'Would cleanup: Order {order.order_id} '
                        f'(expired at {order.payment_expires_at})'
                    )
                return

            # Perform actual cleanup
            cleanup_results = OrderService.cleanup_expired_payments()

            # Report results
            self.stdout.write(
                self.style.SUCCESS(
                    f'Cleanup completed successfully!\n'
                    f'Processed: {cleanup_results["processed_count"]} orders\n'
                    f'Failed: {cleanup_results["failed_count"]} orders'
                )
            )

            # Show errors if any
            if cleanup_results['errors']:
                self.stdout.write(
                    self.style.ERROR('Errors encountered:')
                )
                for error in cleanup_results['errors']:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Order {error["order_id"]}: {error["error"]}'
                        )
                    )

            # Verbose output
            if options['verbose']:
                self.stdout.write('\nDetailed cleanup results:')
                self.stdout.write(f'Total expired orders found: {expired_count}')
                self.stdout.write(f'Successfully processed: {cleanup_results["processed_count"]}')
                self.stdout.write(f'Failed to process: {cleanup_results["failed_count"]}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Cleanup failed: {str(e)}')
            )
            logger.error(f'Management command cleanup failed: {str(e)}')
            raise
