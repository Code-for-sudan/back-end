from django.core import mail
from django.test import TestCase, override_settings
from accounts.tasks import send_email_task
import tempfile

class SendEmailTaskTests(TestCase):
    """
    Test suite for the send_email_task Celery task.

    Tests included:
        - test_send_plain_text_email: Test sending a plain text email to a recipient.
        - test_send_email_with_attachment: Test sending an email with a PDF attachment.
        - test_missing_recipients: Test handling of missing recipients (should fail).
        - test_invalid_attachment_path: Test handling of an invalid attachment file path (should fail).
        - test_wrong_attachment_type: Test handling of an attachment with the wrong type (should fail).
        - test_large_file_attachment: Test sending an email with a large file attachment (5MB).

    Each test checks for correct task status, email delivery, and attachment handling.
    """

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_plain_text_email(self):
        result = send_email_task(
            recipients=['test@example.com'],
            subject='Test Subject',
            body='Test Body'
        )
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test Subject')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email_with_attachment(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'Test PDF content')
            tmp.flush()
            result = send_email_task(
                recipients=['test@example.com'],
                subject='With Attachment',
                body='See attached.',
                attachments=[{'filename': 'test.pdf', 'path': tmp.name, 'mimetype': 'application/pdf'}]
            )
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].attachments), 1)

    def test_missing_recipients(self):
        result = send_email_task(
            recipients=[],
            subject='No Recipients',
            body='Body'
        )
        self.assertEqual(result['status'], 'failure')

    def test_invalid_attachment_path(self):
        result = send_email_task(
            recipients=['test@example.com'],
            subject='Bad Attachment',
            body='Body',
            attachments=[{'filename': 'nofile.pdf', 'path': '/not/a/real/file.pdf'}]
        )
        self.assertEqual(result['status'], 'failure')

    def test_wrong_attachment_type(self):
        result = send_email_task(
            recipients=['test@example.com'],
            subject='Wrong Attachment Type',
            body='Body',
            attachments=['not-a-dict']
        )
        self.assertEqual(result['status'], 'failure')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_large_file_attachment(self):
        # Create a large file in memory (e.g., 5MB)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'A' * (5 * 1024 * 1024))  # 5MB
            tmp.flush()
            result = send_email_task(
                recipients=['test@example.com'],
                subject='Large Attachment',
                body='Body',
                attachments=[{'filename': 'largefile.bin', 'path': tmp.name, 'mimetype': 'application/octet-stream'}]
            )
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].attachments), 1)