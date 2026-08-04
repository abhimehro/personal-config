========== ELIR ==========
PURPOSE: The `end_headers` function in the Alldebrid server was updated to consistently enforce the `ALD_ALLOWED_ORIGINS` CORS configuration, regardless of whether Basic Authentication is enabled or disabled.
SECURITY: Eliminates an overly permissive CORS policy (`Access-Control-Allow-Origin: *`) that was present when authentication was disabled. This ensures the server does not unintentionally expose data cross-origin when the fallback state is reached, closing a potential CSRF/data leakage vulnerability.
FAILS IF: The user relies on legacy behavior where unauthenticated endpoints could be accessed unconditionally by cross-origin web applications not specified in the `ALD_ALLOWED_ORIGINS` environment variable.
VERIFY: Verify the updated tests in `tests/test_http_response_splitting.py` (specifically `test_no_auth_restricts_origins`) pass successfully.
MAINTAIN: If users report CORS issues when authentication is disabled, ensure they are properly configuring the `ALD_ALLOWED_ORIGINS` environment variable with their intended frontend domains instead of relying on the removed fallback wildcard policy.
