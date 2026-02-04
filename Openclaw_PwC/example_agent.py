"""
PWC AI Assistant - Example Agent

Demonstrates how to use the comprehensive PC control tools with LangChain.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_agent():
    """Create a LangChain agent with all PC control tools."""
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent
    from tools import TOOLS

    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )

    # Create agent with all tools
    agent = create_react_agent(
        llm,
        TOOLS,
        state_modifier=(
            "You are a helpful AI assistant that can control the user's PC. "
            "You have access to tools for file operations, web browsing, "
            "Office documents (Excel/Word), and application control. "
            "Always explain what you're doing and ask for confirmation before "
            "destructive operations like deleting files or killing processes."
        ),
    )

    return agent


def run_interactive():
    """Run interactive chat session."""
    agent = create_agent()

    print("=" * 60)
    print("PWC AI Assistant - PC Control Demo")
    print("=" * 60)
    print("Type your request (or 'quit' to exit)")
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            # Run agent
            result = agent.invoke({
                "messages": [("user", user_input)]
            })

            # Print response
            last_message = result["messages"][-1]
            print(f"\nAssistant: {last_message.content}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def run_single_query(query: str):
    """Run a single query and print the result."""
    agent = create_agent()

    print(f"Query: {query}")
    print("-" * 40)

    result = agent.invoke({
        "messages": [("user", query)]
    })

    for msg in result["messages"]:
        role = msg.type if hasattr(msg, "type") else "unknown"
        content = msg.content if hasattr(msg, "content") else str(msg)
        print(f"[{role}] {content[:500]}...")


# Example test scenarios
EXAMPLE_QUERIES = [
    "Downloads 폴더의 파일 목록을 보여줘",
    "Python LangGraph에 대해 검색해줘",
    "현재 실행 중인 프로세스 목록 보여줘",
    "시스템 정보 알려줘",
]


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Run with command line argument
        query = " ".join(sys.argv[1:])
        run_single_query(query)
    else:
        # Interactive mode
        run_interactive()
