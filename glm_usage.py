#!/usr/bin/env python3
"""GLM Coding Plan usage checker for sleepless-agent."""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime


def get_glm_usage():
    """Query GLM API for usage percentage."""
    base_url = os.environ.get('ANTHROPIC_BASE_URL', '')
    auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN', '')

    if not auth_token:
        return "Error: ANTHROPIC_AUTH_TOKEN not set"

    if not base_url:
        return "Error: ANTHROPIC_BASE_URL not set"

    # Determine platform
    if 'api.z.ai' in base_url:
        base_domain = 'https://api.z.ai'
    elif 'open.bigmodel.cn' in base_url or 'dev.bigmodel.cn' in base_url:
        base_domain = 'https://open.bigmodel.cn'
    else:
        return "Error: Unsupported ANTHROPIC_BASE_URL"

    # Quota limit endpoint
    quota_url = f"{base_domain}/api/monitor/usage/quota/limit"

    # Create request
    req = urllib.request.Request(quota_url)
    req.add_header('Authorization', auth_token)
    req.add_header('Accept-Language', 'en-US,en')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            limits = data.get('data', {}).get('limits', [])

            for item in limits:
                if item.get('type') == 'TOKENS_LIMIT':
                    percentage = item.get('percentage', 0)
                    # Return format: "25% used"
                    return f"{percentage}% used"

            return "Usage data not found"
    except urllib.error.HTTPError as e:
        return f"HTTP Error: {e.code}"
    except urllib.error.URLError as e:
        return f"Network Error: {e.reason}"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == '__main__':
    result = get_glm_usage()
    print(result)
