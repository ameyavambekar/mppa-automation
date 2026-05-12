import re
import time
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TESTMAIL_API_KEY = os.getenv("TESTMAIL_API_KEY")
TESTMAIL_NAMESPACE = os.getenv("TESTMAIL_NAMESPACE")
TESTMAIL_TAG = os.getenv("TESTMAIL_TAG", "mppa_test")

TESTMAIL_API_URL = "https://api.testmail.app/api/json"


def get_test_email() -> str:
    """Returns the inbox address to use during registration/login."""
    return f"{TESTMAIL_NAMESPACE}.{TESTMAIL_TAG}@inbox.testmail.app"


def get_otp_from_testmail(retries: int = 10, delay: int = 6) -> str:
    """
    Polls testmail.app API and extracts 6-digit OTP from the latest email.
    Retries up to `retries` times with `delay` seconds between attempts.
    """
    timestamp_before = int(time.time() * 1000)  # ms — ignore emails older than this

    for attempt in range(1, retries + 1):
        print(f"[OTP] Polling attempt {attempt}/{retries}...")

        try:
            response = requests.get(
                TESTMAIL_API_URL,
                params={
                    "apikey": TESTMAIL_API_KEY,
                    "namespace": TESTMAIL_NAMESPACE,
                    "livequery": "true",   # waits up to 30s server-side for new mail
                    "timestamp_from": timestamp_before,
                },
                timeout=35,  # slightly above livequery wait
            )
            response.raise_for_status()
            data = response.json()

            emails = data.get("emails", [])
            if emails:
                # Most recent email first
                latest = sorted(emails, key=lambda e: e["timestamp"], reverse=True)[0]
                body = latest.get("text", "") or latest.get("html", "")

                otp_match = re.search(r'\b(\d{6})\b', body)
                if otp_match:
                    print(f"[OTP] Found OTP: {otp_match.group(1)}")
                    return otp_match.group(1)
                else:
                    print("[OTP] Email received but no 6-digit OTP found in body.")

        except requests.exceptions.Timeout:
            print("[OTP] Request timed out — server livequery returned nothing yet.")
        except requests.exceptions.RequestException as e:
            print(f"[OTP] API request failed: {e}")

        time.sleep(delay)

    raise TimeoutError(
        f"OTP not received after {retries} attempts. "
        f"Check inbox at: https://testmail.app/console"
    )