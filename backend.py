import os
import json
import asyncio
from contextlib import asynccontextmanager, AsyncExitStack
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # 导入 CORS
from pydantic import BaseModel
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# === 配置 ===
# Load environment variables from a .env file (if present) and from the environment.
load_dotenv()

# Try a few common environment variable names for the API key to be flexible.
API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

if not API_KEY or API_KEY in ("", "sk-", "your-api-key-here"):
    raise RuntimeError(
        "API key not set. Please add your API key to network-mcp/.env (DEEPSEEK_API_KEY) or set the environment variable."
    )

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

mcp_session = None
mcp_exit_stack = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_session, mcp_exit_stack
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_tool.py"], 
        env=os.environ
    )
    mcp_exit_stack = AsyncExitStack()
    try:
        read, write = await mcp_exit_stack.enter_async_context(stdio_client(server_params))
        mcp_session = await mcp_exit_stack.enter_async_context(ClientSession(read, write))
        await mcp_session.initialize()
        print("✅ Backend 已连接到 MCP Search Server")
        yield
    finally:
        print("🛑 正在关闭 MCP 连接...")
        await mcp_exit_stack.aclose()

app = FastAPI(lifespan=lifespan)

# ==========================================
# ✅ 修复 CORS 问题
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允许任何前端访问
    allow_credentials=True,
    allow_methods=["*"], # 允许 GET, POST, OPTIONS
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: list = []

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    if not mcp_session:
        raise HTTPException(status_code=500, detail="MCP Server 未连接")

    try:
        tools_list = await mcp_session.list_tools()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工具列表失败: {str(e)}")

    openai_tools = [{
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.inputSchema
        }
    } for t in tools_list.tools]

    messages = [{"role": "system", "content": "你是一个联网助手。请回答用户问题。"}]
    messages.append({"role": "user", "content": req.message})

    print(f"收到用户请求: {req.message}")

    for i in range(5):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=openai_tools,
                tool_choice="auto"
            )
        except Exception as e:
            return {"response": f"模型调用出错: {e}"}
        
        msg = response.choices[0].message
        
        if not msg.tool_calls:
            return {"response": msg.content}
        
        messages.append(msg)
        
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            print(f"🔧 调用工具: {fn_name}")
            
            try:
                result = await mcp_session.call_tool(fn_name, arguments=fn_args)
                tool_content = result.content[0].text
            except Exception as e:
                tool_content = f"工具调用失败: {str(e)}"
                print(f"📄 [搜索结果内容 preview]: {tool_content[:100]}...")
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": fn_name,
                "content": tool_content
            })
            
    return {"response": "思考超时或步骤过多"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)