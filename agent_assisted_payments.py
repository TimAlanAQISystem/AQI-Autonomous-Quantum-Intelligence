import os
from twilio.rest import Client

# Twilio credentials from environment variables
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')

# Initialize Twilio client
client = Client(account_sid, auth_token)

def create_payment_session(call_sid, status_callback_url):
    """
    Create a Payment session for an active call.
    This requires an active call SID from a voice call.
    """
    try:
        payment = client.calls(call_sid).payments.create(
            idempotency_key='unique-session-key-' + str(os.urandom(8).hex()),
            status_callback=status_callback_url,
            payment_method='credit-card',
            charge_amount=10.00,  # Example charge amount
            currency='USD',
            description='Agent X AI Service Payment'
        )

        print(f"Payment session created successfully!")
        print(f"Payment SID: {payment.sid}")
        print(f"Call SID: {payment.call_sid}")
        print(f"Date Created: {payment.date_created}")

        return payment.sid

    except Exception as e:
        print(f"Error creating payment session: {str(e)}")
        return None

def update_payment_capture(payment_sid, call_sid, capture_type, status_callback_url):
    """
    Update payment session to capture specific payment information.
    capture_type can be: 'payment-card-number', 'expiration-date', 'security-code', 'postal-code'
    """
    try:
        payment = client.calls(call_sid).payments(payment_sid).update(
            capture=capture_type,
            idempotency_key='unique-capture-key-' + str(os.urandom(8).hex()),
            status_callback=status_callback_url
        )

        print(f"Payment capture updated for {capture_type}")
        print(f"Payment SID: {payment.sid}")

    except Exception as e:
        print(f"Error updating payment capture: {str(e)}")

def complete_payment_session(payment_sid, call_sid, status_callback_url):
    """
    Complete the payment session to process the payment.
    """
    try:
        payment = client.calls(call_sid).payments(payment_sid).update(
            status='complete',
            idempotency_key='unique-complete-key-' + str(os.urandom(8).hex()),
            status_callback=status_callback_url
        )

        print(f"Payment session completed successfully!")
        print(f"Payment SID: {payment.sid}")

    except Exception as e:
        print(f"Error completing payment session: {str(e)}")

def cancel_payment_session(payment_sid, call_sid, status_callback_url):
    """
    Cancel the payment session.
    """
    try:
        payment = client.calls(call_sid).payments(payment_sid).update(
            status='cancel',
            idempotency_key='unique-cancel-key-' + str(os.urandom(8).hex()),
            status_callback=status_callback_url
        )

        print(f"Payment session cancelled!")
        print(f"Payment SID: {payment.sid}")

    except Exception as e:
        print(f"Error cancelling payment session: {str(e)}")

def demonstrate_payment_workflow():
    """
    Demonstrate the complete payment workflow.
    Note: This requires an active call SID from a voice call.
    For demonstration, we'll use a placeholder call SID.
    """

    # Placeholder - replace with actual call SID from an active voice call
    call_sid = 'CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'  # Replace with real call SID
    status_callback_url = 'https://your-app.com/payment-status'  # Replace with your callback URL

    print("=== Agent-Assisted Payment Workflow Demo ===")
    print("Note: This requires an active voice call. Replace call_sid with a real active call SID.")
    print()

    # Step 1: Create payment session
    print("Step 1: Creating payment session...")
    payment_sid = create_payment_session(call_sid, status_callback_url)

    if not payment_sid:
        print("Failed to create payment session. Exiting.")
        return

    print()

    # Step 2: Capture credit card number
    print("Step 2: Requesting credit card number...")
    update_payment_capture(payment_sid, call_sid, 'payment-card-number', status_callback_url)
    print("Agent would now ask customer to enter card number via phone keypad")
    print()

    # Step 3: Capture expiration date
    print("Step 3: Requesting expiration date...")
    update_payment_capture(payment_sid, call_sid, 'expiration-date', status_callback_url)
    print("Agent would now ask customer to enter expiration date (MMYY)")
    print()

    # Step 4: Capture security code
    print("Step 4: Requesting security code...")
    update_payment_capture(payment_sid, call_sid, 'security-code', status_callback_url)
    print("Agent would now ask customer to enter CVV/security code")
    print()

    # Step 5: Complete the payment
    print("Step 5: Completing payment session...")
    complete_payment_session(payment_sid, call_sid, status_callback_url)
    print("Payment processed through Twilio's PCI-compliant system")
    print()

    print("=== Workflow Complete ===")
    print("Status callbacks would be sent to your application for real-time updates")

if __name__ == "__main__":
    # Check if credentials are available
    if not account_sid or not auth_token:
        print("Error: Missing Twilio credentials. Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables.")
        exit(1)

    demonstrate_payment_workflow()