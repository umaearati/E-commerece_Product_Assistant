# import asyncio
# from langchain_mcp_adapters.client import MultiServerMCPClient

# async def main():
#     client = MultiServerMCPClient({
#         "hybrid_search": {   # server name
#             "command": "python",
#             "args": [
#                 "/Users/nanimahi/E-commerce-Product-Assistant/mcp_servers/product_search_server.py"
#             ],  # absolute path
#             "transport": "stdio",
#         }
#     })

#     # Discover tools
#     tools = await client.get_tools()
#     print("Available tools:", [t.name for t in tools])

#     # Pick tools by name
#     retriever_tool = next(t for t in tools if t.name == "get_product_info")
#     web_tool = next(t for t in tools if t.name == "web_search")

#     # --- Step 1: Try retriever first ---
#     #query = "Samsung Galaxy S25 price"
#     # query = "iPhone 15"
#     query = "iPhone 17?"
#     retriever_result = await retriever_tool.ainvoke({"query": query})
#     print("\nRetriever Result:\n", retriever_result)

#     # --- Step 2: Fallback to web search if retriever fails ---
#     if not retriever_result.strip() or "No local results found." in retriever_result:
#         print("\n No local results, falling back to web search...\n")
#         web_result = await web_tool.ainvoke({"query": query})
#         print("Web Search Result:\n", web_result)

# if __name__ == "__main__":
#     asyncio.run(main())



import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    client = MultiServerMCPClient({
        "hybrid_search": {
            "command": "python",
            "args": [
                "/Users/nanimahi/E-commerce-Product-Assistant/mcp_servers/product_search_server.py"
            ],
            "transport": "stdio",
        }
    })

    tools = await client.get_tools()
    print("Available tools:", [t.name for t in tools])

    retriever_tool = next(t for t in tools if t.name == "get_product_info")
    web_tool = next(t for t in tools if t.name == "web_search")

    query = "iPhone 17?"

    retriever_result = await retriever_tool.ainvoke({"query": query})

    retriever_text = ""
    if retriever_result and len(retriever_result) > 0:
        retriever_text = retriever_result[0].get("text", "")

    print("\nRetriever Result:\n", retriever_text)

    if not retriever_text.strip() or "No local results found." in retriever_text:
        print("\nNo local results, falling back to web search...\n")

        web_result = await web_tool.ainvoke({"query": query})
        web_text = web_result[0]["text"] if web_result else ""

        print("Web Search Result:\n", web_text)


if __name__ == "__main__":
    asyncio.run(main())