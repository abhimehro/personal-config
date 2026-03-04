import base64
import timeit
import secrets

AUTH_USER = "admin_user_long_name"
AUTH_PASS = "super_secret_password_12345"
EXPECTED_TOKEN = base64.b64encode(f"{AUTH_USER}:{AUTH_PASS}".encode()).decode()

def test_old():
    auth_data = EXPECTED_TOKEN
    decoded = base64.b64decode(auth_data).decode('utf-8')
    username, password = decoded.split(':', 1)
    user_match = secrets.compare_digest(username, AUTH_USER)
    pass_match = secrets.compare_digest(password, AUTH_PASS)
    return user_match and pass_match

def test_new():
    auth_data = EXPECTED_TOKEN
    return secrets.compare_digest(auth_data, EXPECTED_TOKEN)

if __name__ == "__main__":
    old_time = timeit.timeit(test_old, number=1000000)
    new_time = timeit.timeit(test_new, number=1000000)

    print(f"Old: {old_time:.4f}s")
    print(f"New: {new_time:.4f}s")
    print(f"Speedup: {old_time / new_time:.2f}x")
