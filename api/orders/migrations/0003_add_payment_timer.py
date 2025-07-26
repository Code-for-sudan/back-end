# Generated migration for payment timer functionality

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_order_accounttype'),  # Replace with your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_expires_at',
            field=models.DateTimeField(blank=True, help_text='Payment deadline for under_paying orders', null=True),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status', 'payment_expires_at'], name='orders_order_status_expires_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['payment_expires_at'], name='orders_order_payment_exp_idx'),
        ),
    ]
