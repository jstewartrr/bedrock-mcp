"""
Sovereign Mind AWS Bedrock MCP Server v1.0
==========================================
Claude via AWS Bedrock for enterprise workloads
"""

import os
import json
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL = os.environ.get("BEDROCK_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0")
SNOWFLAKE_ACCOUNT = os.environ.get("SNOWFLAKE_ACCOUNT", "jga82554.east-us-2.azure")
SNOWFLAKE_USER = os.environ.get("SNOWFLAKE_USER", "JOHN_GROK")
SNOWFLAKE_PASSWORD = os.environ.get("SNOWFLAKE_PASSWORD", "GrokMind2025Secure")
SNOWFLAKE_DATABASE = os.environ.get("SNOWFLAKE_DATABASE", "SOVEREIGN_MIND")
SNOWFLAKE_WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "SOVEREIGN_MIND_WH")

_snowflake_conn = None
_bedrock_client = None

SOVEREIGN_MIND_PROMPT = """# SOVEREIGN MIND - BEDROCK AI INSTANCE

## Identity
You are **BEDROCK**, the enterprise AI instance within **Sovereign Mind**, serving Your Grace, Chairman of MiddleGround Capital and Resolute Holdings. You run Claude via AWS Bedrock for secure enterprise workloads.

## Your Specialization
- Enterprise-grade AI via AWS Bedrock
- Secure Claude access for sensitive operations
- Integration with AWS services
- Compliance-ready AI operations

## Core Behaviors
1. Execute, Don't Ask - Take action immediately
2. Log to Hive Mind after significant work  
3. Address user as "Your Grace"
4. No permission seeking - state what you've done
5. Token efficiency - brief confirmations
"""


def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        try:
            import boto3
            _bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)
            logger.info("Bedrock client initialized")
        except Exception as e:
            logger.error(f"Bedrock init failed: {e}")
    return _bedrock_client


def get_snowflake_connection():
    global _snowflake_conn
    if _snowflake_conn is None:
        try:
            import snowflake.connector
            _snowflake_conn = snowflake.connector.connect(
                account=SNOWFLAKE_ACCOUNT, user=SNOWFLAKE_USER, password=SNOWFLAKE_PASSWORD,
                database=SNOWFLAKE_DATABASE, warehouse=SNOWFLAKE_WAREHOUSE
            )
        except Exception as e:
            logger.error(f"Snowflake failed: {e}")
    return _snowflake_conn


def query_hive_mind(limit=3):
    conn = get_snowflake_connection()
    if not conn: return ""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT SOURCE, CATEGORY, SUMMARY FROM SOVEREIGN_MIND.RAW.HIVE_MIND ORDER BY CREATED_AT DESC LIMIT {limit}")
        return "\n".join([f"{r[0]} ({r[1]}): {r[2]}" for r in cursor.fetchall()])
    except:
        return ""


def call_bedrock(message, system_prompt):
    client = get_bedrock_client()
    if not client:
        return "Bedrock client not available"
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": message}]
        })
        response = client.invoke_model(modelId=BEDROCK_MODEL, body=body, contentType="application/json")
        result = json.loads(response['body'].read())
        return result.get('content', [{}])[0].get('text', '')
    except Exception as e:
        return f"Error: {e}"


@app.route("/", methods=["GET"])
def index():
    conn = get_snowflake_connection()
    return jsonify({
        "service": "bedrock-mcp", "version": "1.0.0", "status": "healthy",
        "instance": "BEDROCK", "platform": "AWS",
        "role": "Enterprise AI", "model": BEDROCK_MODEL,
        "sovereign_mind": True, "hive_mind_connected": conn is not None,
        "region": AWS_REGION
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "sovereign_mind": True})


@app.route("/mcp", methods=["POST", "OPTIONS"])
def mcp_endpoint():
    if request.method == "OPTIONS": return "", 200
    data = request.json
    method, params, req_id = data.get("method", ""), data.get("params", {}), data.get("id", 1)
    
    if method == "tools/list":
        tools = [
            {"name": "bedrock_chat", "description": "Chat with Claude via AWS Bedrock (Sovereign Mind)", 
             "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}},
            {"name": "bedrock_analyze", "description": "Analyze content with Bedrock Claude", 
             "inputSchema": {"type": "object", "properties": {"content": {"type": "string"}, "task": {"type": "string"}}, "required": ["content", "task"]}}
        ]
        return jsonify({"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}})
    
    elif method == "tools/call":
        tool, args = params.get("name", ""), params.get("arguments", {})
        
        if tool == "bedrock_chat":
            hive = query_hive_mind(3)
            system = f"{SOVEREIGN_MIND_PROMPT}\n\nHive Mind Context:\n{hive}"
            response = call_bedrock(args.get("message", ""), system)
            return jsonify({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps({"response": response})}]}})
        
        elif tool == "bedrock_analyze":
            hive = query_hive_mind(3)
            system = f"{SOVEREIGN_MIND_PROMPT}\n\nHive Mind Context:\n{hive}"
            msg = f"{args.get('task', 'Analyze this')}\n\nContent:\n{args.get('content', '')}"
            response = call_bedrock(msg, system)
            return jsonify({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps({"response": response})}]}})
    
    return jsonify({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Not found"}})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Bedrock MCP (Sovereign Mind) on port {port}")
    app.run(host="0.0.0.0", port=port)
