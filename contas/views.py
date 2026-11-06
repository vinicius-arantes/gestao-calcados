from django.contrib.auth.views import LoginView

from .forms import LoginForm


class EntrarView(LoginView):
    template_name = 'contas/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True
