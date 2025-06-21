from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """
        Called when the Django app is ready; imports the accounts.signals module to ensure signal handlers are registered.
        """
        import accounts.signals
