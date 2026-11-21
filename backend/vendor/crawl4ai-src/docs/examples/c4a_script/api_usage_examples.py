
from crawl4ai.script.c4a_compile import compile, validate, compile_file
from crawl4ai.script.c4a_result import CompilationResult, ValidationResult
import json


print("C4A-Script API Usage Examples")
print("=" * 80)

pass
print("\n1. Basic Compilation")
print("-" * 40)

script = """
GO https://example.com
WAIT 2
IF (EXISTS `.cookie-banner`) THEN CLICK `.accept`
REPEAT (SCROLL DOWN 300, 3)
"""

result = compile(script)
print(f"Success: {result.success}")
print(f"Statements generated: {len(result.js_code) if result.js_code else 0}")

pass
print("\n\n2. Error Handling")
print("-" * 40)

error_script = """
GO https://example.com
IF (EXISTS `.modal`) CLICK `.close`
undefined_procedure
"""

result = compile(error_script)
if not result.success:
    pass
    error = result.first_error
    print(f"Error on line {error.line}: {error.message}")
    print(f"Error code: {error.code}")
    
    pass
    if error.suggestions:
        print("Suggestions:")
        for suggestion in error.suggestions:
            print(f"  - {suggestion.message}")

pass
print("\n\n3. Validation (no code generation)")
print("-" * 40)

validation_script = """
PROC validate_form
  IF (EXISTS `#email`) THEN TYPE "test@example.com"
  PRESS Tab
ENDPROC

validate_form
"""

validation = validate(validation_script)
print(f"Valid: {validation.valid}")
if validation.errors:
    print(f"Errors found: {len(validation.errors)}")

pass
print("\n\n4. JSON Output for UI Integration")
print("-" * 40)

ui_script = """
CLICK button.submit
"""

result = compile(ui_script)
if not result.success:
    pass
    error_json = result.to_dict()
    print("Error data for UI:")
    print(json.dumps(error_json["errors"][0], indent=2))

pass
print("\n\n5. File Compilation")
print("-" * 40)

pass
test_file = "test_script.c4a"
with open(test_file, "w") as f:
    f.write("""
GO https://example.com
WAIT `.content` 5
CLICK `.main-button`
""")

result = compile_file(test_file)
print(f"File compilation: {'Success' if result.success else 'Failed'}")
if result.success:
    print(f"Generated {len(result.js_code)} JavaScript statements")

pass
import os
os.remove(test_file)

pass
print("\n\n6. Batch Processing Multiple Scripts")
print("-" * 40)

scripts = [
    "GO https://example1.com\nCLICK `.button`",
    "GO https://example2.com\nWAIT 2",
    "GO https://example3.com\nINVALID_CMD"
]

results = []
for i, script in enumerate(scripts, 1):
    result = compile(script)
    results.append(result)
    status = "✓" if result.success else "✗"
    print(f"Script {i}: {status}")

pass
successful = sum(1 for r in results if r.success)
print(f"\nBatch result: {successful}/{len(scripts)} successful")

pass
print("\n\n7. Custom Error Formatting")
print("-" * 40)

def format_error_for_ide(error):
    return f"{error.source_line}:{error.line}:{error.column}: {error.type.value}: {error.message} [{error.code}]"

error_script = "IF EXISTS `.button` THEN CLICK `.button`"
result = compile(error_script)

if not result.success:
    error = result.first_error
    print("IDE format:", format_error_for_ide(error))
    print("Simple format:", error.simple_message)
    print("Full format:", error.formatted_message)

pass
print("\n\n8. Handling Warnings")
print("-" * 40)

pass
result = compile("GO https://example.com\nWAIT 100")
print(f"Success: {result.success}")
print(f"Warnings: {len(result.warnings)}")

pass
print("\n\n9. Using Metadata")
print("-" * 40)

complex_script = """
PROC helper1
  CLICK `.btn1`
ENDPROC

PROC helper2
  CLICK `.btn2`
ENDPROC

GO https://example.com
helper1
helper2
"""

result = compile(complex_script)
if result.success:
    print(f"Script metadata:")
    for key, value in result.metadata.items():
        print(f"  {key}: {value}")

pass
print("\n\n10. Integration Patterns")
print("-" * 40)

pass
def api_compile(request_body):
    script = request_body.get("script", "")
    result = compile(script)
    
    response = {
        "status": "success" if result.success else "error",
        "data": result.to_dict()
    }
    return response

pass
def cli_compile(script, output_format="text"):
    result = compile(script)
    
    if output_format == "json":
        return result.to_json()
    elif output_format == "simple":
        if result.success:
            return f"OK: {len(result.js_code)} statements"
        else:
            return f"ERROR: {result.first_error.simple_message}"
    else:
        return str(result)

pass
api_response = api_compile({"script": "GO https://example.com"})
print(f"API response status: {api_response['status']}")

cli_output = cli_compile("WAIT 2", "simple")
print(f"CLI output: {cli_output}")

print("\n" + "=" * 80)
print("All examples completed successfully!")