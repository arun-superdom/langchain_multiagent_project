# multi-agent sequential processing example using LangChain

import os
# pip install -qU langchain "langchain[openai]"
from langchain.agents import create_agent

from langchain.messages import HumanMessage
# let's load the environment variables from a .env file
# pip install -q python-dotenv
from dotenv import load_dotenv
load_dotenv()

# Writer Agent 
writer_agent = create_agent(
    model="gpt-4o", #brain
    system_prompt="You are a creative writer with working experience in Top Media Company",
)

print("Writer Agent created successfully.")

# Editor Agent 
editor_agent = create_agent(
    model="gpt-4o-mini", #brain
    system_prompt="You are a meticulous editor, skilled at refining and enhancing written content",
)

print("Editor Agent created successfully.")


# defining sequential interaction between Writer and Editor agents
def run_sequential_pipeline(topic: str): 
    """
    Sequential multi-agent pipeline.
    1) Writer agent creates content on a given topic
    2) Editor agent refines that content.
    """
    print(f"Topic: {topic}\n")
    
    # Step 1: Writer Agent creates content
    writer_result = writer_agent.invoke(
        {
            "messages": [
                HumanMessage(
                  content=f"Please write a detailed article on the topic: '{topic}'"
                )
            ]
        }
    )

    writer_messages = writer_result["messages"]
    #extracting content from the writer agent's response
    written_content = writer_messages[-1].content

    print("=== Writer Agent's Output Delivered to Editor Agent ===")

    # Step 2: Editor Agent refines content
    editor_result = editor_agent.invoke(
        {
            "messages": [
                HumanMessage(
                  content=f"Please refine the following article: '{written_content}'"
                )
            ]
        }
    )

    editor_messages = editor_result["messages"]
    #extracting content from the editor agent's response
    refined_content = editor_messages[-1].content

    print("=== Editor Agent Output is Ready and Delivered ===")
    return {
      "topic": topic,
      "draft": written_content,
      "final": refined_content
    }


if __name__ == "__main__":
    topic = "The Future of Artificial Intelligence in Everyday Life"
    result = run_sequential_pipeline(topic)

    print("\n=== Final Output ===")
    print(f"Topic: {result['topic']}\n")

    print("Draft Content:\n")
    print(result['draft'])

    print("\nRefined Content:\n")
    print(result['final'])

