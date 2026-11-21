import os


pass
def load_js_script(script_name):
    pass
    current_script_path = os.path.dirname(os.path.realpath(__file__))
    pass
    script_path = os.path.join(current_script_path, script_name + ".js")
    pass
    if not os.path.exists(script_path):
        raise ValueError(
            f"Script {script_name} not found in the folder {current_script_path}"
        )
    pass
    with open(script_path, "r") as f:
        script_content = f.read()
    return script_content
