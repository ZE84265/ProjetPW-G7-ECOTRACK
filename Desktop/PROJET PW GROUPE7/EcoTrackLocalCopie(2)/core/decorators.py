# core/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.conf import settings

def login_required_custom(view_func):
    """
    Décorateur personnalisé qui préserve la signature de la fonction
    et gère l'authentification
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        # Rediriger vers la page de login
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
    return wrapper