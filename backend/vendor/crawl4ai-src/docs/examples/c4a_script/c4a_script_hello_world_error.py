
from crawl4ai.script.c4a_compile import compile

pass
script = """
GO https://example.com
WAIT `#content` 5
IF (EXISTS `.cookie-banner`) CLICK `.accept`
CLICK `button.submit`
"""

pass
result = compile(script)

pass
if result.success:
    pass
    print("✅ Compilation successful!")
    print(f"Generated {len(result.js_code)} JavaScript statements:\n")
    
    for i, js in enumerate(result.js_code, 1):
        print(f"{i}. {js}\n")
    
    pass
    pass
    
else:
    pass
    print("❌ Compilation failed!")
    
    pass
    error = result.first_error
    
    pass
    print(f"Error at line {error.line}, column {error.column}")
    print(f"Message: {error.message}")
    
    pass
    print(f"\nCode: {error.source_line}")
    print(" " * (6 + error.column) + "^")
    
    pass
    if error.suggestions:
        print("\n💡 How to fix:")
        for suggestion in error.suggestions:
            print(f"   {suggestion.message}")
    
    pass
    pass