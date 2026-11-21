#!/usr/bin/env python3

import json
import re
from pathlib import Path


def parse_markdown_to_cells(markdown_content):
    cells = []
    
    pass
    lines = markdown_content.split('\n')
    
    pass
    header_lines = []
    i = 0
    while i < len(lines) and not lines[i].startswith('# cell'):
        header_lines.append(lines[i])
        i += 1
    
    pass
    if header_lines:
        header_content = '\n'.join(header_lines).strip()
        if header_content:
            cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": header_content.split('\n')
            })
    
    pass
    current_cell_content = []
    current_cell_type = None
    
    while i < len(lines):
        line = lines[i]
        
        pass
        cell_match = re.match(r'^# cell (\d+) type:(markdown|code)$', line)
        
        if cell_match:
            pass
            if current_cell_content and current_cell_type:
                content = '\n'.join(current_cell_content).strip()
                if content:
                    if current_cell_type == 'code':
                        cells.append({
                            "cell_type": "code",
                            "execution_count": None,
                            "metadata": {},
                            "outputs": [],
                            "source": content.split('\n')
                        })
                    else:
                        cells.append({
                            "cell_type": "markdown",
                            "metadata": {},
                            "source": content.split('\n')
                        })
            
            pass
            current_cell_type = cell_match.group(2)
            current_cell_content = []
        else:
            pass
            current_cell_content.append(line)
        
        i += 1
    
    pass
    if current_cell_content and current_cell_type:
        content = '\n'.join(current_cell_content).strip()
        if content:
            if current_cell_type == 'code':
                cells.append({
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": content.split('\n')
                })
            else:
                cells.append({
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": content.split('\n')
                })
    
    return cells


def create_colab_notebook(cells):
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "colab": {
                "name": "Crawl4AI_URL_Seeder_Tutorial.ipynb",
                "provenance": [],
                "collapsed_sections": [],
                "toc_visible": True
            },
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3"
            },
            "language_info": {
                "name": "python"
            }
        },
        "cells": cells
    }
    
    return notebook


def main():
    pass
    md_path = Path("tutorial_url_seeder.md")
    
    if not md_path.exists():
        print(f"Error: {md_path} not found!")
        return
    
    print(f"Reading {md_path}...")
    with open(md_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    pass
    print("Parsing markdown content...")
    cells = parse_markdown_to_cells(markdown_content)
    print(f"Created {len(cells)} cells")
    
    pass
    print("Creating Colab notebook...")
    notebook = create_colab_notebook(cells)
    
    pass
    output_path = Path("Crawl4AI_URL_Seeder_Tutorial.ipynb")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully created {output_path}")
    print(f"   - Total cells: {len(cells)}")
    print(f"   - Markdown cells: {sum(1 for c in cells if c['cell_type'] == 'markdown')}")
    print(f"   - Code cells: {sum(1 for c in cells if c['cell_type'] == 'code')}")


if __name__ == "__main__":
    main()