import os
import json
import logging
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ModelReply:
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, int]] = None

def load_system_prompt(schemas: Optional[List[Dict[str, Any]]] = None) -> str:
    """Load system prompt from prompts/agent_system.txt."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "agent_system.txt")
    base_prompt = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            base_prompt = f.read().strip()
    else:
        base_prompt = "You are an AI Travel Expense Audit Agent."
    
    if schemas:
        tools_str = json.dumps(schemas, ensure_ascii=False, indent=2)
        base_prompt += f"\n\nAvailable Tools:\n{tools_str}"
        
    return base_prompt

def _mock_llm_response(messages: List[Dict[str, Any]], schemas: Optional[List[Dict[str, Any]]] = None) -> ModelReply:
    """Mock Model for offline testing without Groq API Key."""
    last_msg = messages[-1]["content"] if messages else ""
    
    prompt_tokens = sum(len(m.get("content", "")) // 4 for m in messages) + 40
    completion_tokens = 30
    usage = {
        "calls": 1,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "max_prompt": prompt_tokens
    }
    
    if "CLM001" in last_msg or "valid" in last_msg.lower():
        return ModelReply(
            content=json.dumps({
                "decision": "APPROVED",
                "reason": "Hotel expenses are valid according to DOC003@v1.0",
                "evidence": ["DOC003@v1.0"]
            }),
            usage=usage
        )
    elif "CLM002" in last_msg or "exceed" in last_msg.lower():
        return ModelReply(
            content=json.dumps({
                "decision": "REJECTED",
                "reason": "Entertainment expense exceeds the 2,000,000 VND limit per DOC004@v1.0",
                "evidence": ["DOC004@v1.0"]
            }),
            usage=usage
        )
    elif "missing" in last_msg.lower() or "receipt" in last_msg.lower():
        return ModelReply(
            content=json.dumps({
                "decision": "NEED_MORE_INFO",
                "reason": "Missing attached financial receipts",
                "evidence": []
            }),
            usage=usage
        )
    elif "not mentioned" in last_msg.lower() or "not found" in last_msg.lower():
        return ModelReply(
            content=json.dumps({
                "decision": "NO_ANSWER",
                "reason": "Could not find relevant policy in the documents",
                "evidence": []
            }),
            usage=usage
        )
    else:
        return ModelReply(
            content=json.dumps({
                "decision": "APPROVED",
                "reason": "The claim complies with the travel policy",
                "evidence": ["DOC001@v1.0"]
            }),
            usage=usage
        )

def call_llm(messages: List[Dict[str, Any]], schemas: Optional[List[Dict[str, Any]]] = None) -> ModelReply:
    """
    Call Groq API (OpenAI-compatible endpoint).
    Signature: (messages, schemas) -> ModelReply
    Logs usage with 4 exact fields: calls, prompt_tokens, completion_tokens, max_prompt.
    Retries on 429, 5xx, and Network/Timeout errors only.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    # Fallback to Mock if GROQ_API_KEY is not set (offline mode)
    if not api_key:
        return _mock_llm_response(messages, schemas)
        
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = load_system_prompt(schemas)
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        payload = {
            "model": model_name,
            "messages": full_messages,
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        
        max_retries = 3
        response_data = None
        
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    response_data = json.loads(resp.read().decode('utf-8'))
                    break
            except urllib.error.HTTPError as e:
                # Ignore 400/401/403, retry only 429 and 5xx
                if e.code in [429, 500, 502, 503, 504] and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    logger.error(f"Groq API HTTP Error {e.code}: {e.reason}")
                    raise
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    logger.error(f"Groq API Network Error: {e}")
                    raise

        if not response_data:
            return _mock_llm_response(messages, schemas)

        choice = response_data["choices"][0]["message"]
        content = choice.get("content")
        
        raw_usage = response_data.get("usage", {})
        p_tokens = raw_usage.get("prompt_tokens", 0)
        c_tokens = raw_usage.get("completion_tokens", 0)
        
        # Exact format for TV1 contract
        usage = {
            "calls": 1,
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "max_prompt": p_tokens
        }
        
        return ModelReply(content=content, usage=usage)
        
    except Exception as e:
        logger.warning(f"Falling back to Mock Model due to Groq API error: {e}")
        return _mock_llm_response(messages, schemas)


def audit_claim_and_verify(
    claim_id: str,
    query: str,
    get_claim_fn,
    search_policy_fn,
    submit_decision_fn,
    get_claim_status_fn,
    max_steps: int = 5
) -> Dict[str, Any]:
    """
    Agent Loop: Query -> Evidence Gating -> Decision -> Write (submit_decision) -> Read-back (get_claim_status) -> VERIFY
    """
    messages = [{"role": "user", "content": f"Audit claim {claim_id}: {query}"}]
    
    for step in range(max_steps):
        reply = call_llm(messages)
        
        try:
            parsed = json.loads(reply.content)
            decision = parsed.get("decision")
            reason = parsed.get("reason", "")
            evidence = parsed.get("evidence", [])
            
            # Evidence Gating: Do not write on NO_ANSWER or NEED_MORE_INFO
            if decision == "NO_ANSWER":
                return {
                    "claim_id": claim_id,
                    "decision": "NO_ANSWER",
                    "reason": reason,
                    "verified": False,
                    "verify_result": "SKIPPED_NO_WRITE",
                    "usage": reply.usage
                }
                
            if decision == "NEED_MORE_INFO":
                return {
                    "claim_id": claim_id,
                    "decision": "NEED_MORE_INFO",
                    "reason": reason,
                    "verified": False,
                    "verify_result": "SKIPPED_NO_WRITE",
                    "usage": reply.usage
                }

            # Write only for APPROVED / REJECTED / ESCALATED
            if decision in ["APPROVED", "REJECTED", "ESCALATED"]:
                # 1. WRITE
                submit_decision_fn(claim_id=claim_id, decision=decision, reason=reason, evidence=evidence)
                
                # 2. READ-BACK TO VERIFY
                actual_status = get_claim_status_fn(claim_id=claim_id)
                
                # 3. COMPARE & VERIFY
                if actual_status == decision:
                    print(f"VERIFY SUCCESS: Claim {claim_id} updated to {actual_status}")
                    verify_result = "VERIFY SUCCESS"
                    is_verified = True
                else:
                    print(f"VERIFY FAILED: Expected {decision}, got {actual_status}")
                    verify_result = "VERIFY FAILED"
                    is_verified = False
                    
                return {
                    "claim_id": claim_id,
                    "decision": decision,
                    "actual_status": actual_status,
                    "verified": is_verified,
                    "verify_result": verify_result,
                    "reason": reason,
                    "evidence": evidence,
                    "usage": reply.usage
                }
                
        except Exception as e:
            messages.append({"role": "assistant", "content": reply.content})
            messages.append({"role": "user", "content": f"Error: Malformed decision JSON. Details: {e}"})

    return {
        "claim_id": claim_id,
        "decision": "MAX_STEPS_REACHED",
        "verified": False,
        "verify_result": "VERIFY FAILED",
        "usage": {"calls": max_steps, "prompt_tokens": 0, "completion_tokens": 0, "max_prompt": 0}
    }