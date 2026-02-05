"""
LLM client with logging and retry logic.
"""
import os
import time
from openai import AzureOpenAI
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

api_version = os.getenv("AZURE_OPENAI_API_VERSION")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
subscription_key = os.getenv("AZURE_API_KEY")
client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")


def call_llm(prompt: str, temperature: float = 0, max_retries: int = 3, timeout: int = 60):
    """
    Call LLM with logging, retry logic, and timing.
    
    Args:
        prompt: Input prompt
        temperature: LLM temperature (0 = deterministic)
        max_retries: Number of retry attempts
        timeout: Request timeout in seconds
    
    Returns:
        LLM response content
    """
    prompt_preview = prompt[:100].replace('\n', ' ') + "..." if len(prompt) > 100 else prompt
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            logger.debug(f"LLM request (attempt {attempt + 1}/{max_retries}): {prompt_preview}")
            
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                timeout=timeout
            )
            
            elapsed = time.time() - start_time
            content = response.choices[0].message.content
            
            # Log success
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            logger.debug(f"LLM response received in {elapsed:.1f}s ({tokens_used} tokens)")
            
            return content
            
        except Exception as e:
            logger.warning(f"LLM request failed (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"LLM request failed after {max_retries} attempts")
                raise
    
    raise RuntimeError("LLM call failed after all retries")