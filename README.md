# cassyy

A simple Apereo Central Authentication Service (CAS) client that provides basic
support for validating service tickets using CAS Protocols 2/3. It uses the
Python standard library `urllib.request` module and has no external
dependencies.

# Usage

Below provides just an example of how it might be used in a web
application. The example is generic and does not represent any specific web
framework. It is up to the application to decide what `service_url` it will
use with the `build_login_url` method. It is common to use the current request
url or a fixed url that CAS will redirect the user to after the login is
successful along with a `ticket` that can be validated to retrieve information
about the user.

```python
import cassyy

cas_client = cassyy.CASClient.from_base_url('https://cas.example.org')

def login_route(request, response):
    redirect_url = ...
    target_url = cas_client.build_login_url(redirect_url)
    response.redirect(target_url)

# This could be a route or some authentication middleware that intercepts
# unauthenticated requests and redirects to CAS and/or validates a CAS ticket
# if one is included in the request.
def validate_route(request, response):
    ticket = ...  # pull from request
    service_url = ...
    cas_user = cas_client.validate(service_url, ticket)
    request.session['user'] = cas_user.asdict()

def logout_route(request, response):
    # where to have CAS redirect back to the app after the CAS logout occurs,
    # or None to use the CAS logout page
    service_url = ...
    target_url = cas_client.build_logout_url(service_url)
    response.redirect(target_url)
```
