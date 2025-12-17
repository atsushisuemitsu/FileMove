"""OpenRouter API Client - Generate Python scripts from prompts"""

import re
import httpx
from typing import Optional


class OpenRouterClient:
    """Client for OpenRouter API"""

    def __init__(self, api_url: str, api_key: str, model: str):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.Client(timeout=60.0)
        return self._client

    def update_config(self, api_url: str, api_key: str, model: str):
        """Update API configuration"""
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    def generate_script(self, prompt: str) -> tuple[bool, str]:
        """
        Generate Python script from prompt.

        Returns:
            tuple[bool, str]: (success, script_content or error_message)
        """
        if not self.api_key:
            return False, "API key is not configured"

        system_prompt = """You are a Python code generator. Generate only valid, executable Python code.
Do not include any explanations, markdown formatting, or code blocks.
Output only the raw Python code that can be directly saved and executed.
Include appropriate imports at the top of the script.
Add error handling where appropriate.
The script should be self-contained and runnable."""

        try:
            client = self._get_client()
            response = client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/FileMove",
                    "X-Title": "FileMove Script Generator"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
            )

            if response.status_code != 200:
                return False, f"API error: {response.status_code} - {response.text}"

            data = response.json()

            if "choices" not in data or not data["choices"]:
                return False, "No response from API"

            content = data["choices"][0]["message"]["content"]

            # Clean up the response - remove markdown code blocks if present
            script = self._extract_code(content)

            return True, script

        except httpx.TimeoutException:
            return False, "API request timed out"
        except httpx.RequestError as e:
            return False, f"Network error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def _extract_code(self, content: str) -> str:
        """Extract Python code from response, removing markdown if present"""
        # Try to extract from code blocks
        patterns = [
            r'```python\s*\n(.*?)```',
            r'```py\s*\n(.*?)```',
            r'```\s*\n(.*?)```',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()

        # If no code blocks, return as-is (assuming it's raw code)
        return content.strip()

    def close(self):
        """Close the HTTP client"""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
