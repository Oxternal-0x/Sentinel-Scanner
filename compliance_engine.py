import os
import logging
import json
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment from standard locations (supports .env and .evn)
load_dotenv(dotenv_path='.env', override=False)
load_dotenv(dotenv_path='.evn', override=True)

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI SDK not available")
    OPENAI_AVAILABLE = False


class LegalInterpreter:
    """
    Interprets regulatory text and converts it into compliance rules.
    Uses an OpenAI-compatible model for legal language processing.
    """
    
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI SDK is required. Run 'pip install openai'.")

        base_url = (
            os.getenv("DEEPSEEK_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
        )
        api_key = (
            os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENAI_KEY")
        )
        self.model = (
            os.getenv("COMPLIANCE_MODEL")
            or os.getenv("DEEPSEEK_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4o"
        )

        if not api_key:
            if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
                # Ollama often runs without a real key, but the SDK requires one.
                api_key = "ollama"
            else:
                raise ValueError(
                    "No API key found. Set DEEPSEEK_API_KEY or OPENAI_API_KEY."
                )

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(**client_kwargs)
        
        # The system prompt is the "Secret Sauce" for high-accuracy extraction
        self.system_instructions = (
            "You are a Senior Blockchain Compliance Officer. "
            "Extract key compliance requirements from regulatory text and format them as a structured JSON object. "
            "Focus on: required functions (e.g., pause, freeze, blacklist), prohibited patterns, "
            "ownership constraints, and any specific technical requirements. "
            "Return a JSON object with compliance rules that can be used to audit smart contracts."
        )

    @staticmethod
    def _extract_json_object(raw: str) -> Dict:
        if not raw:
            raise ValueError("Empty model response")
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in model response")
        return json.loads(raw[start : end + 1])

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.1,
    ) -> Dict:
        """
        Generate JSON from an OpenAI-compatible model.
        Tries strict JSON mode first, then falls back for providers that don't support it.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as strict_exc:
            logger.info(
                "Strict JSON response_format unsupported or failed (%s); retrying without it.",
                strict_exc,
            )
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        content = response.choices[0].message.content
        return self._extract_json_object(content or "")

    def translate_law_to_rules(self, legal_text: str) -> Dict:
        """
        Uses the configured model to translate messy legal prose into 
        structured logic that our scanner can understand.
        
        Args:
            legal_text: Regulatory or legal text to interpret
            
        Returns:
            Dictionary containing extracted compliance rules
        """
        if not hasattr(self, 'client') or not self.client:
            logger.warning("OpenAI client not available - returning basic rules")
            return {
                "regulatory_text": legal_text,
                "extracted_rules": ["Unable to analyze - OpenAI client not available"],
                "confidence": 0.0,
                "status": "CLIENT_UNAVAILABLE"
            }
        
        try:
            result = self.generate_json(
                messages=[
                    {"role": "system", "content": self.system_instructions},
                    {"role": "user", "content": f"Extract compliance rules from this regulatory text: {legal_text}"}
                ],
                max_tokens=1000,
                temperature=0.1  # Low temperature for consistent rule extraction
            )

            # Ensure the result has expected structure
            if not isinstance(result, dict):
                result = {"extracted_rules": [str(result)]}
            
            # Add metadata
            result["original_text"] = legal_text
            result["extraction_timestamp"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to interpret law: {e}")
            return {
                "error": f"Failed to interpret law: {str(e)}",
                "original_text": legal_text
            }


# Example Usage for Windsurf to index:
# interpreter = LegalInterpreter()
# rules = interpreter.translate_law_to_rules("MiCA Article 12: Stablecoins must have a pause function.")
