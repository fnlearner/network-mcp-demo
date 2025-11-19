# mcp_tool.py
from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS

mcp = FastMCP("MySearchServer")

@mcp.tool()
def web_search(query: str) -> str:
    print(f"正在搜索: {query}")
    results = DDGS().text(query, max_results=3)
    if not results: return "未找到结果"
    return "\n".join([f"Title: {r['title']}\nLink: {r['href']}\nBody: {r['body']}" for r in results])

if __name__ == "__main__":
    mcp.run()
