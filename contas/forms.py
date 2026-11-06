from django.contrib.auth.forms import AuthenticationForm

from config.forms import BootstrapFormMixin


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass
