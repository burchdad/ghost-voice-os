"""
Webhook Signature Verification
Validates authenticity of webhooks from Telnyx and Twilio
"""

import hmac
import hashlib
import logging
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)


class WebhookVerifier:
    """Verify webhook signatures from telephony providers"""

    @staticmethod
    def verify_twilio_signature(
        auth_token: str,
        request_url: str,
        post_params: Dict[str, str],
        twilio_signature: str
    ) -> bool:
        """
        Verify Twilio X-Twilio-Signature header
        
        Args:
            auth_token: Twilio auth token from environment
            request_url: Full URL of webhook endpoint
            post_params: POST parameters from request
            twilio_signature: X-Twilio-Signature header value
            
        Returns:
            True if signature is valid
        """
        try:
            # Concatenate URL and parameters in Twilio's expected order
            s = request_url
            
            # Sort params alphabetically by key and append
            for k in sorted(post_params.keys()):
                s += k + post_params[k]
            
            # Create HMAC-SHA1 hash
            mac = hmac.new(
                auth_token.encode(),
                s.encode(),
                hashlib.sha1
            )
            computed_signature = mac.digest()
            
            # Compare with provided signature (base64 decoded)
            import base64
            provided_signature = base64.b64decode(twilio_signature)
            
            is_valid = hmac.compare_digest(computed_signature, provided_signature)
            
            if is_valid:
                logger.info("✅ [TWILIO] Signature verified")
            else:
                logger.warning("❌ [TWILIO] Signature verification failed")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ [TWILIO] Signature verification error: {e}")
            return False

    @staticmethod
    def verify_telnyx_signature(
        api_key: str,
        request_body: str,
        telnyx_signature: str
    ) -> bool:
        """
        Verify Telnyx webhook signature
        
        Telnyx uses the format: timestamp.hash
        Where hash = HMAC-SHA-256(timestamp + body, api_key)
        
        Args:
            api_key: Telnyx API key from environment
            request_body: Raw request body as string
            telnyx_signature: Telnyx-Signature header (format: timestamp.hash)
            
        Returns:
            True if signature is valid
        """
        try:
            # Parse timestamp and signature
            if "." not in telnyx_signature:
                logger.warning("❌ [TELNYX] Invalid signature format")
                return False
            
            timestamp_str, provided_hash = telnyx_signature.split(".", 1)
            
            # Reconstruct message to sign: timestamp + body
            message = f"{timestamp_str}{request_body}"
            
            # Compute HMAC-SHA256
            computed_hash = hmac.new(
                api_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare hashes
            is_valid = hmac.compare_digest(computed_hash, provided_hash)
            
            if is_valid:
                logger.info("✅ [TELNYX] Signature verified")
            else:
                logger.warning("❌ [TELNYX] Signature verification failed")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ [TELNYX] Signature verification error: {e}")
            return False


def get_webhook_verifier() -> WebhookVerifier:
    """Factory function for webhook verifier"""
    return WebhookVerifier()
