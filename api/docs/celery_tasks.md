## Celery Email Task

### Purpose

Send plain text emails or emails with attachments to one or more recipients using Django and Celery.

### Task Signature

```python
send_email_task(recipients, subject, body, attachments=None)
```

### Parameters

- **recipients** (`list`): List of recipient email addresses (required).
- **subject** (`str`): Email subject (required).
- **body** (`str`): Email body as plain text (required).
- **attachments** (`list`, optional): List of dicts, each with:
  - `filename`: Name for the attachment in the email.
  - `path`: Filesystem path to the file.
  - `mimetype`: MIME type (e.g., `'application/pdf'`, `'text/csv'`).

### Behavior

- Sends plain text emails if no attachments are provided.
- Sends emails with attachments if provided, reading files from the filesystem.
- Uses Django’s `DEFAULT_FROM_EMAIL` as the sender.
- Supports multiple recipients.

### Return Value

- `{'status': 'success'}` on success.
- `{'status': 'failure', 'reason': ...}` on failure.

### Logging

- Logs errors for missing/invalid recipients, attachment failures, and email sending failures.
- Logs info on successful email sending.

### Queue

- Task is routed to the `email` Celery queue.

### Usage Example

```python
# Plain text email
send_email_task.delay(
    recipients=['user@example.com'],
    subject='Hello',
    body='This is a test email.'
)

# Email with attachments
send_email_task.delay(
    recipients=['user@example.com'],
    subject='Invoice',
    body='Please see attached.',
    attachments=[
        {'filename': 'invoice.pdf', 'path': '/path/to/invoice.pdf', 'mimetype': 'application/pdf'}
    ]
)
```

### Testing

Unit tests cover:

- Sending plain text emails.
- Sending emails with attachments.
- Handling missing recipients.
- Handling invalid attachment paths.
- Handling wrong attachment types.
- Handling large file attachments.

### Requirements

- Django email backend must be configured.
- Celery worker must be running and listening to the `email` queue.
- Attachment files must exist and be accessible by the worker.
