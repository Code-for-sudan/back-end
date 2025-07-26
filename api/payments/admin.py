from django.contrib import admin
from .models import PaymentGateway, Payment, PaymentAttempt, Refund


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    """Admin configuration for PaymentGateway model"""
    list_display = [
        'name', 'gateway_type', 'is_active', 'is_test_mode',
        'fixed_fee', 'percentage_fee', 'created_at'
    ]
    list_filter = ['gateway_type', 'is_active', 'is_test_mode']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'gateway_type', 'is_active', 'is_test_mode')
        }),
        ('Fee Structure', {
            'fields': ('fixed_fee', 'percentage_fee')
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin configuration for Payment model"""
    list_display = [
        'payment_id', 'order_reference', 'user', 'amount', 'currency',
        'payment_method', 'status', 'gateway', 'created_at', 'processed_at'
    ]
    list_filter = [
        'status', 'payment_method', 'gateway__gateway_type',
        'created_at', 'processed_at'
    ]
    search_fields = [
        'payment_id', 'order_reference', 'user__email',
        'gateway_transaction_id', 'gateway_reference'
    ]
    readonly_fields = [
        'payment_id', 'fee_amount', 'net_amount', 'created_at',
        'updated_at', 'processed_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'payment_id', 'order_reference', 'user', 'gateway'
            )
        }),
        ('Amount Details', {
            'fields': ('amount', 'currency', 'fee_amount', 'net_amount')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'status', 'failure_reason')
        }),
        ('Gateway Information', {
            'fields': ('gateway_transaction_id', 'gateway_reference'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'gateway')


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    """Admin configuration for PaymentAttempt model"""
    list_display = [
        'payment', 'attempt_number', 'status', 'attempted_at'
    ]
    list_filter = ['status', 'attempted_at']
    search_fields = ['payment__payment_id', 'error_message']
    readonly_fields = ['attempted_at']
    
    fieldsets = (
        ('Attempt Information', {
            'fields': ('payment', 'attempt_number', 'status')
        }),
        ('Result', {
            'fields': ('error_message', 'attempted_at')
        }),
        ('Gateway Response', {
            'fields': ('gateway_response',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('payment')


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    """Admin configuration for Refund model"""
    list_display = [
        'refund_id', 'payment', 'amount', 'status',
        'initiated_by', 'created_at', 'processed_at'
    ]
    list_filter = ['status', 'created_at', 'processed_at']
    search_fields = [
        'refund_id', 'payment__payment_id', 'payment__order_reference',
        'reason', 'initiated_by__email'
    ]
    readonly_fields = ['refund_id', 'created_at', 'processed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Refund Information', {
            'fields': ('refund_id', 'payment', 'amount', 'status')
        }),
        ('Details', {
            'fields': ('reason', 'initiated_by')
        }),
        ('Gateway Information', {
            'fields': ('gateway_refund_id',),
            'classes': ('collapse',)
        }),
        ('Gateway Response', {
            'fields': ('gateway_response',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'payment', 'initiated_by'
        )


# Custom admin actions
def mark_payments_as_completed(modeladmin, request, queryset):
    """Admin action to mark payments as completed (for testing)"""
    updated = queryset.filter(status='pending').update(status='completed')
    modeladmin.message_user(
        request,
        f'{updated} payments were successfully marked as completed.'
    )

mark_payments_as_completed.short_description = "Mark selected payments as completed"

def mark_payments_as_failed(modeladmin, request, queryset):
    """Admin action to mark payments as failed (for testing)"""
    updated = queryset.filter(status='pending').update(status='failed')
    modeladmin.message_user(
        request,
        f'{updated} payments were successfully marked as failed.'
    )

mark_payments_as_failed.short_description = "Mark selected payments as failed"

# Add actions to PaymentAdmin
PaymentAdmin.actions = [mark_payments_as_completed, mark_payments_as_failed]
