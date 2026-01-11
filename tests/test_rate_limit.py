"""
Test script to verify rate limiting is working
Run this while your Flask app is running
"""

import requests
import time
import re

BASE_URL = "http://127.0.0.1:8080/"


def get_csrf_token(session, url):
    """Extract CSRF token from a page"""
    try:
        response = session.get(url)
        # Look for CSRF token in meta tag or hidden input
        match = re.search(r'name="csrf_token".*?value="([^"]+)"', response.text)
        if match:
            return match.group(1)
        
        # Try meta tag
        match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
        if match:
            return match.group(1)
        
        return None
    except Exception as e:
        print(f"  Error getting CSRF token: {e}")
        return None


def test_login_rate_limit():
    """Test login endpoint rate limiting"""
    print("=" * 60)
    print("TESTING LOGIN RATE LIMIT (5 per 15 minutes)")
    print("=" * 60)
    print()
    
    # Try to login 7 times (should fail on 6th attempt)
    for i in range(1, 8):
        print(f"Attempt {i}...")
        
        # Create new session for each attempt
        session = requests.Session()
        
        # Get CSRF token
        csrf_token = get_csrf_token(session, f"{BASE_URL}/login")
        
        data = {
            'identifier': 'test@example.com',
            'password': 'wrongpassword'
        }
        
        if csrf_token:
            data['csrf_token'] = csrf_token
        
        response = session.post(
            f"{BASE_URL}/login",
            data=data,
            allow_redirects=False
        )
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 429:
            print(f"  ✓ Rate limit triggered on attempt {i}")
            if 'Retry-After' in response.headers:
                print(f"  Retry-After: {response.headers['Retry-After']}")
            break
        elif response.status_code == 200 or response.status_code == 302:
            print(f"  ✓ Request {i} processed (login failed as expected)")
        elif response.status_code == 500:
            print(f"  ✗ Server error - check Flask console logs")
            print(f"  Response: {response.text[:200]}")
        else:
            print(f"  Response: {response.status_code}")
        
        time.sleep(0.5)
    
    print()


def test_register_rate_limit():
    """Test registration endpoint rate limiting"""
    print("=" * 60)
    print("TESTING REGISTER RATE LIMIT (3 per hour)")
    print("=" * 60)
    print()
    
    # Try to register 5 times (should fail on 4th attempt)
    for i in range(1, 6):
        print(f"Attempt {i}...")
        
        # Create new session
        session = requests.Session()
        
        # Get CSRF token
        csrf_token = get_csrf_token(session, f"{BASE_URL}/register")
        
        data = {
            'name': 'Test User',
            'email': f'test{i}@example.com',
            'student_id': f'TEST00{i}',
            'password': 'TestPassword123',
            'confirm_password': 'TestPassword123'
        }
        
        if csrf_token:
            data['csrf_token'] = csrf_token
        
        response = session.post(
            f"{BASE_URL}/register",
            data=data,
            allow_redirects=False
        )
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 429:
            print(f"  ✓ Rate limit triggered on attempt {i}")
            break
        elif response.status_code == 200 or response.status_code == 302:
            print(f"  ✓ Request {i} processed")
        elif response.status_code == 500:
            print(f"  ✗ Server error - check Flask console logs")
        else:
            print(f"  Response: {response.status_code}")
        
        time.sleep(0.5)
    
    print()


def test_upvote_rate_limit():
    """Test upvote endpoint rate limiting"""
    print("=" * 60)
    print("TESTING UPVOTE RATE LIMIT (30 per minute)")
    print("=" * 60)
    print()
    
    # Try to upvote 35 times (should fail after 30)
    fake_complaint_id = "test_complaint_123"
    
    for i in range(1, 36):
        response = requests.post(
            f"{BASE_URL}/complaint/{fake_complaint_id}/upvote",
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 429:
            print(f"✓ Rate limit triggered on attempt {i}")
            print(f"  This is correct - limit is 30 per minute")
            try:
                data = response.json()
                print(f"  Error message: {data.get('error')}")
            except:
                pass
            break
        elif i % 10 == 0:
            print(f"  Attempt {i}: {response.status_code}")
        
        time.sleep(0.05)
    
    print()


def test_simple_rate_limit():
    """Test a simple endpoint to verify rate limiting works"""
    print("=" * 60)
    print("TESTING SIMPLE ENDPOINT (/test-rate-limit)")
    print("=" * 60)
    print()
    
    print("Attempting to access /test-rate-limit 5 times...")
    print("(Should succeed 3 times, then get rate limited)")
    print()
    
    for i in range(1, 6):
        response = requests.get(f"{BASE_URL}/test-rate-limit")
        
        print(f"Attempt {i}: {response.status_code}", end="")
        
        if response.status_code == 429:
            print(f" - ✓ Rate limited!")
            break
        elif response.status_code == 200:
            print(f" - ✓ Success")
        elif response.status_code == 404:
            print(f" - Route not found (add test route to app.py)")
            break
        else:
            print(f" - Unexpected: {response.status_code}")
        
        time.sleep(0.5)
    
    print()


def check_rate_limit_headers():
    """Check if rate limit headers are present"""
    print("=" * 60)
    print("CHECKING RATE LIMIT HEADERS")
    print("=" * 60)
    print()
    
    response = requests.get(f"{BASE_URL}/")
    
    print("Response headers related to rate limiting:")
    rate_limit_headers = {}
    for header, value in response.headers.items():
        if 'rate' in header.lower() or 'limit' in header.lower():
            print(f"  {header}: {value}")
            rate_limit_headers[header] = value
    
    if not rate_limit_headers:
        print("  ⚠️  No rate limit headers found")
    else:
        print(f"\n✓ Found {len(rate_limit_headers)} rate limit headers")
    
    print()


if __name__ == "__main__":
    print("🧪 RATE LIMITING TEST SUITE (WITH CSRF)")
    print()
    print("Make sure your Flask app is running on http://127.0.0.1:8080/")
    print()
    input("Press Enter to start tests...")
    print()
    
    # Run tests
    check_rate_limit_headers()
    test_simple_rate_limit()
    test_login_rate_limit()
    test_register_rate_limit()
    test_upvote_rate_limit()
    
    print("=" * 30)
    print("✅ TESTS COMPLETE")
    print("=" * 30)
    print()
    print("Expected results:")
    print("  ✓ Login should be blocked after 5 attempts")
    print("  ✓ Register should be blocked after 3 attempts")
    print("  ✓ Upvote should be blocked after 30 attempts")
    print()
    print("If you see 500 errors:")
    print("  1. Check your Flask console for error messages")
    print("  2. The CSRF token might not be configured correctly")
    print("  3. Share the error logs and we'll fix it together")