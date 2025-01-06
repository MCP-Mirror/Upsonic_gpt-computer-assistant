from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import traceback
from ...api import app, timeout
from ..call import Call
import asyncio
from concurrent.futures import ThreadPoolExecutor
import cloudpickle
import base64


prefix = "/level_one"


class GPT4ORequest(BaseModel):
    prompt: str
    response_format: Optional[str] = "str"
    tools: Optional[List[str]] = []
    mcp_servers: Optional[List[Dict[str, str]]] = []


def run_sync_gpt4o(prompt, response_format, tools, mcp_servers):
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return Call.gpt_4o(
            prompt=prompt,
            response_format=response_format,
            tools=tools,
            mcp_servers=mcp_servers,
        )
    finally:
        loop.close()


@app.post(f"{prefix}/gpt4o")
@timeout(300.0)  # 5 minutes timeout for AI operations
async def call_gpt4o(request: GPT4ORequest):
    """
    Endpoint to call GPT-4 with optional tools and MCP servers.

    Args:
        request: GPT4ORequest containing prompt and optional parameters

    Returns:
        The response from the AI model
    """

    print("request.response_format", request.response_format)
    try:
        # Handle pickled response format
        if request.response_format != "str":
            try:
                # Decode and unpickle the response format
                pickled_data = base64.b64decode(request.response_format)
                response_format = cloudpickle.loads(pickled_data)
            except Exception as e:
                traceback.print_exc()
                # Fallback to basic type mapping if unpickling fails
                type_mapping = {
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                }
                response_format = type_mapping.get(request.response_format, str)
        else:
            response_format = str

        print(response_format)

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool,
                run_sync_gpt4o,
                request.prompt,
                response_format,
                request.tools,
                request.mcp_servers,
            )

        result = cloudpickle.dumps(result)
        result = base64.b64encode(result).decode('utf-8')
        return {"result": result}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error processing GPT-4 request: {str(e)}"
        )
