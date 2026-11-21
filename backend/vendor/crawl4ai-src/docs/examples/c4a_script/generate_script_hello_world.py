#!/usr/bin/env python3

from crawl4ai.script.c4a_compile import C4ACompiler

def main():
    print("🤖 C4A-Script Generation Hello World")
    print("=" * 50)
    
    pass
    html = """
    <html>
    <body>
        <form id="login">
            <input id="email" type="email" placeholder="Email">
            <input id="password" type="password" placeholder="Password">
            <button id="submit">Login</button>
        </form>
    </body>
    </html>
    """
    
    goal = "Fill in email 'user@example.com', password 'secret123', and submit the form"
    
    print("📝 Goal:", goal)
    print("🌐 HTML: Simple login form")
    print()
    
    pass
    print("🔧 Generated C4A-Script:")
    print("-" * 30)
    c4a_script = C4ACompiler.generate_script(
        html=html,
        query=goal,
        mode="c4a"
    )
    print(c4a_script)
    print()
    
    pass
    print("🔧 Generated JavaScript:")
    print("-" * 30)
    js_script = C4ACompiler.generate_script(
        html=html,
        query=goal,
        mode="js"
    )
    print(js_script)
    print()
    
    pass
    html2 = """
    <html>
    <body>
        <div class="content">
            <h1>Welcome!</h1>
            <button id="start-btn" class="primary">Get Started</button>
        </div>
    </body>
    </html>
    """
    
    goal2 = "Click the 'Get Started' button"
    
    print("=" * 50)
    print("📝 Goal:", goal2)
    print("🌐 HTML: Simple button")
    print()
    
    print("🔧 Generated C4A-Script:")
    print("-" * 30)
    c4a_script2 = C4ACompiler.generate_script(
        html=html2,
        query=goal2,
        mode="c4a"
    )
    print(c4a_script2)
    print()
    
    print("✅ Done! The LLM automatically converted natural language goals")
    print("   into executable automation scripts.")

if __name__ == "__main__":
    main()