"""
Test script for Stripe webhook and membership upgrade
"""
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get your test user email
TEST_USER_EMAIL = input("Enter your test user email: ").strip()

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "https://deepfakedetection-production-ab9b.up.railway.app")

def test_manual_upgrade():
    """Test the manual upgrade endpoint"""
    print(f"\n🧪 Testing manual upgrade for {TEST_USER_EMAIL}...")
    
    response = requests.post(
        f"{BACKEND_URL}/api/manual-upgrade",
        params={
            "user_email": TEST_USER_EMAIL,
            "plan": "pro_monthly"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Manual upgrade successful!")
        print(f"   Status: {data.get('message')}")
        print(f"   Expires: {data.get('expires')}")
        return True
    else:
        print(f"❌ Manual upgrade failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_webhook_simulation():
    """Simulate a Stripe webhook event"""
    print(f"\n🧪 Simulating Stripe webhook for {TEST_USER_EMAIL}...")
    
    # Create a mock Stripe checkout.session.completed event
    mock_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer_email": TEST_USER_EMAIL,
                "metadata": {
                    "user_email": TEST_USER_EMAIL,
                    "plan": "pro_monthly"
                }
            }
        }
    }
    
    response = requests.post(
        f"{BACKEND_URL}/api/stripe-webhook",
        json=mock_event,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        print("✅ Webhook processed successfully!")
        print(f"   Response: {response.json()}")
        return True
    else:
        print(f"❌ Webhook processing failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def verify_user_status():
    """Verify the user's membership status"""
    print(f"\n🔍 Verifying membership status...")
    
    # Note: You'll need to be logged in for this to work
    # This is just a placeholder - you can manually check in the database
    print("   Please check the user's membership status in your database or via the API")
    print("   The user should now have:")
    print("   - membership_status: 'Pro'")
    print("   - membership_expiry: 30 days from now")

if __name__ == "__main__":
    print("=" * 60)
    print("Stripe Webhook & Membership Upgrade Test")
    print("=" * 60)
    
    # Test 1: Manual upgrade endpoint (easiest way to test)
    if test_manual_upgrade():
        verify_user_status()
    
    print("\n" + "=" * 60)
    print("Testing webhook simulation (without signature verification)...")
    print("=" * 60)
    
    # Test 2: Webhook simulation
    if test_webhook_simulation():
        verify_user_status()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("\nTo test with real Stripe:")
    print("1. Set STRIPE_WEBHOOK_SECRET in Railway")
    print("2. Add webhook endpoint in Stripe Dashboard:")
    print(f"   https://deepfakedetection-production-ab9b.up.railway.app/api/stripe-webhook")
    print("3. Select event: checkout.session.completed")
    print("=" * 60)
