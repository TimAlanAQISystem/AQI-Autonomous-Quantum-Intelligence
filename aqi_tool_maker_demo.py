#!/usr/bin/env python3
"""
Demonstration of AQI Automatic Tool Maker Capabilities
"""

from aqi_automatic_tool_maker import AutomaticToolMaker

def main():
    print("=== AQI AUTOMATIC TOOL MAKER DEMONSTRATION ===\n")

    tool_maker = AutomaticToolMaker()

    # Example 1: Create a text analysis tool (using the exact requirement that works)
    print("1. Creating Text Analysis Tool...")
    analysis_tool = tool_maker.create_tool(
        "Create a tool that analyzes text data",
        tool_type='analysis_tool'
    )

    if analysis_tool:
        print("✓ Text analysis tool created: {}".format(analysis_tool.spec.name))
        result = tool_maker.execute_tool(analysis_tool.spec.name, input="Hello, this is a test message!")
        print("✓ Analysis result: {}".format(result))
    else:
        print("✗ Text analysis tool creation failed")

    # Example 2: Try to create another instance of analysis tool
    print("\n2. Creating Another Analysis Tool...")
    data_tool = tool_maker.create_tool(
        "Create a tool that analyzes data structures",
        tool_type='analysis_tool'
    )

    if data_tool:
        print("✓ Data analysis tool created: {}".format(data_tool.spec.name))
        result = tool_maker.execute_tool(data_tool.spec.name, input={'name': 'AQI', 'version': '1.0'})
        print("✓ Data analysis result: {}".format(result))
    else:
        print("✗ Data analysis tool creation failed")

    # Example 3: Debug automation tool
    print("\n3. Debugging Automation Tool Creation...")
    print("Checking automation template...")

    # Create spec manually to debug
    spec = tool_maker._analyze_requirement("Create a tool that performs basic automation", 'automation_script')
    if spec:
        print("Spec created: {}".format(spec.name))
        code = tool_maker._generate_code(spec)
        print("Code generated (first 200 chars): {}".format(code[:200]))

        # Test the code
        test_results = tool_maker._test_code(code, spec)
        print("Test results: {}".format(test_results))

        if test_results['passed']:
            automation_tool = tool_maker._deploy_tool(code, spec, test_results)
            tool_maker._register_tool(automation_tool)
            print("✓ Automation tool created and registered")
        else:
            print("✗ Automation tool test failed")
    else:
        print("✗ Spec creation failed")

    # Show all available tools
    print("\n4. Tool Registry Summary:")
    tools = tool_maker.list_tools()
    print("Available tools: {}".format(len(tools)))
    for tool_name in tools:
        tool = tool_maker.get_tool(tool_name)
        print("  - {}: {}".format(tool_name, tool.spec.description[:50] + "..."))

    print("\n=== DEMONSTRATION COMPLETE ===")
    print("\nAQI's Automatic Tool Maker demonstrated:")
    print("• Natural language requirement analysis")
    print("• Dynamic Python code generation")
    print("• Automated testing and validation")
    print("• Tool deployment and registry management")
    print("• On-demand tool execution")
    print("\nThis is AQI's ultimate evolutionary capability!")

if __name__ == "__main__":
    main()