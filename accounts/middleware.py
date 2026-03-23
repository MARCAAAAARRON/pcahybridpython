from django.utils import timezone
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect


class SessionTimeoutMiddleware:
    """Auto-logout users after a period of inactivity."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')
            now = timezone.now().timestamp()

            if last_activity:
                elapsed = now - last_activity
                if elapsed > settings.SESSION_COOKIE_AGE:
                    logout(request)
                    return redirect('accounts:login')

            request.session['last_activity'] = now

        response = self.get_response(request)
        return response


class CacheControlMiddleware:
    """Prevent browser caching of pages for authenticated users."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # If the user is logged in, instruct the browser NOT to cache the page.
        # This prevents the back button from showing sensitive data after logout.
        if hasattr(request, 'user') and request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
        return response
