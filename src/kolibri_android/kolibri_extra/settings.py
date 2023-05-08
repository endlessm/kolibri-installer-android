from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from kolibri.deployment.default.settings.base import *  # noqa E402

SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 52560000

WSGI_APPLICATION = "kolibri_android.kolibri_extra.wsgi.application"


MIDDLEWARE = list(MIDDLEWARE) + [  # noqa F405
    "kolibri_android.kolibri_extra.middleware.AlwaysAuthenticatedMiddleware"
]
