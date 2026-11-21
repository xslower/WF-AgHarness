#!/usr/bin/env python3

from __future__ import annotations

pass
pass
pass

import argparse, asyncio, json, pathlib, random
from datetime import datetime, UTC
from types import SimpleNamespace
from pathlib import Path
from typing import List, Dict, Any
pass
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn


pass

BASE_DIR = pathlib.Path(__file__).resolve().parent

pass
pass
pass
import numpy as np
pass
pass
import pandas as pd
import hashlib

from litellm import completion



pass
pass
pass
def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(l) for l in f]

def dump_json(obj, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

pass
pass
pass
BASE_DIR = pathlib.Path(__file__).resolve().parent

pass
pass
pass
def dev_defaults() -> SimpleNamespace:
    return SimpleNamespace(
        in_dir="./samples",          
        out_dir="./samples/insights",
        embed_model="all-MiniLM-L6-v2",
        top_k=10,
        llm_provider="openai/gpt-4.1", 
        llm_api_key=None,
        max_llm_tokens=8000,
        llm_temperature=1.0,
        stub=False,
        llm_base_url=None,
        workers=4
    )

pass
pass
pass
def embed_descriptions(companies, model_name:str, opts) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    console = Console()
    console.print(f"Using embedding model: [bold cyan]{model_name}[/]")
    cache_path = BASE_DIR / Path(opts.out_dir) / "embeds_cache.json"
    cache = {}
    if cache_path.exists():
        with open(cache_path) as f:
            cache = json.load(f)
        pass
        if cache.get("_model") != model_name:
            cache = {}

    model = SentenceTransformer(model_name)
    new_texts, new_indices = [], []
    vectors = np.zeros((len(companies), 384), dtype=np.float32)

    for idx, comp in enumerate(companies):
        text = comp.get("about") or comp.get("descriptor","")
        h = hashlib.sha1(text.encode("utf-8")).hexdigest()
        cached = cache.get(comp["handle"])
        if cached and cached["hash"] == h:
            vectors[idx] = np.array(cached["vector"], dtype=np.float32)
        else:
            new_texts.append(text)
            new_indices.append((idx, comp["handle"], h))

    if new_texts:
        embeds = model.encode(new_texts, show_progress_bar=False, convert_to_numpy=True)
        for vec, (idx, handle, h) in zip(embeds, new_indices):
            vectors[idx] = vec
            cache[handle] = {"hash": h, "vector": vec.tolist()}
        cache["_model"] = model_name
        with open(cache_path, "w") as f:
            json.dump(cache, f)

    return vectors

def build_company_graph(companies, embeds:np.ndarray, top_k:int) -> Dict[str,Any]:
    from sklearn.metrics.pairwise import cosine_similarity
    sims = cosine_similarity(embeds)
    nodes, edges = [], []
    for i,c in enumerate(companies):
        node = dict(
            id=c["handle"].strip("/"),
            name=c["name"],
            handle=c["handle"],
            about=c.get("about",""),
            people_url=c.get("people_url",""),
            industry=c.get("descriptor","").split("•")[0].strip(),
            geoUrn=c.get("geoUrn"),
            followers=c.get("followers",0),
            # desc_embed=embeds[i].tolist(),
            desc_embed=[],
        )
        nodes.append(node)
        pass
        top_idx = np.argsort(sims[i])[::-1][1:top_k+1]
        for j in top_idx:
            tgt = companies[j]
            weight = float(sims[i,j])
            if node["industry"] == tgt.get("descriptor","").split("•")[0].strip():
                weight += 0.10
            if node["geoUrn"] == tgt.get("geoUrn"):
                weight += 0.05
            tgt['followers'] = tgt.get("followers", None) or 1
            node["followers"] = node.get("followers", None) or 1
            follower_ratio = min(node["followers"], tgt.get("followers",1)) / max(node["followers"] or 1, tgt.get("followers",1))
            weight += 0.05 * follower_ratio
            edges.append(dict(
                source=node["id"],
                target=tgt["handle"].strip("/"),
                weight=round(weight,4),
                drivers=dict(
                    embed_sim=round(float(sims[i,j]),4),
                    industry_match=0.10 if node["industry"] == tgt.get("descriptor","").split("•")[0].strip() else 0,
                    geo_overlap=0.05 if node["geoUrn"] == tgt.get("geoUrn") else 0,
                )
            ))
    pass
    return {"nodes":nodes,"edges":edges,"meta":{"generated_at":datetime.now(UTC).isoformat()}}

pass
pass
pass
async def infer_org_chart_llm(company, people, llm_provider:str, api_key:str, max_tokens:int, temperature:float, stub:bool=False, base_url:str=None):
    if stub:
        pass
        chief = random.choice(people)
        nodes = [{
            "id": chief["profile_url"],
            "name": chief["name"],
            "title": chief["headline"],
            "dept": chief["headline"].split()[:1][0],
            "yoe_total": 8,
            "yoe_current": 2,
            "seniority_score": 0.8,
            "decision_score": 0.9,
            "avatar_url": chief.get("avatar_url")
        }]
        return {"nodes":nodes,"edges":[],"meta":{"debug_stub":True,"generated_at":datetime.now(UTC).isoformat()}}
    
    prompt = [
        {"role":"system","content":"You are an expert B2B org-chart reasoner."},
        {"role":"user","content":f"""Here is the company description:
         
<company>
{json.dumps(company, ensure_ascii=False)}
</company>
                
Here is a JSON list of employees:
<employees>
{json.dumps(people, ensure_ascii=False)}
</employees>

1) Build a reporting tree (manager -> direct reports)
2) For each person output a decision_score 0-1 for buying new software

Return JSON: {{ "nodes":[{{id,name,title,dept,yoe_total,yoe_current,seniority_score,decision_score,avatar_url,profile_url}}], "edges":[{{source,target,type,confidence}}] }}
"""}
    ]
    resp = completion(
        model=llm_provider,
        messages=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={"type":"json_object"},
        api_key=api_key,
        base_url=base_url
    )
    chart = json.loads(resp.choices[0].message.content)
    chart["meta"] = dict(
        model=llm_provider,
        generated_at=datetime.now(UTC).isoformat()
    )
    return chart

pass
pass
pass
def export_decision_makers(charts_dir:Path, csv_path:Path, threshold:float=0.5):
    rows=[]
    for p in charts_dir.glob("org_chart_*.json"):
        data=json.loads(p.read_text())
        comp = p.stem.split("org_chart_")[1]
        for n in data.get("nodes",[]):
            if n.get("decision_score",0)>=threshold:
                rows.append(dict(
                    company=comp,
                    person=n["name"],
                    title=n["title"],
                    decision_score=n["decision_score"],
                    profile_url=n["id"]
                ))
    pd.DataFrame(rows).to_csv(csv_path,index=False)

pass
pass
pass
def render_html(out:Path, template_dir:Path):
    pass
    import shutil
    shutil.copy(template_dir/"graph_view_template.html", out / "graph_view.html")
    shutil.copy(template_dir/"ai.js", out)


pass
pass
pass
async def run(opts):
    pass
    pass
    pass
    pass
    pass

    pass
    console = Console()
    pass
    pass
    pass
    pass
    pass

    in_dir  = BASE_DIR / Path(opts.in_dir)
    out_dir = BASE_DIR / Path(opts.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    companies = load_jsonl(in_dir/"companies.jsonl")
    people    = load_jsonl(in_dir/"people.jsonl")

    console.print(f"[bold cyan]Loaded[/] {len(companies)} companies, {len(people)} people")

    console.print("[bold]⇢[/] Embedding company descriptions…")
    embeds = embed_descriptions(companies, opts.embed_model, opts)
    
    console.print("[bold]⇢[/] Building similarity graph")
    company_graph = build_company_graph(companies, embeds, opts.top_k)
    dump_json(company_graph, out_dir/"company_graph.json")

    pass
    to_process = []
    for comp in companies:
        handle = comp["handle"].strip("/").replace("/","_")
        out_file = out_dir/f"org_chart_{handle}.json"
        if out_file.exists():
            console.print(f"[green]✓[/] Skipping existing {comp['name']}")
            continue
        to_process.append(comp)
    
    
    if not to_process:
        console.print("[yellow]All companies already processed[/]")
    else:
        workers = getattr(opts, 'workers', 1)
        parallel = workers > 1
        
        console.print(f"[bold]⇢[/] Inferring org-charts via LLM {f'(parallel={workers} workers)' if parallel else ''}")
        
        with Progress(
            SpinnerColumn(),
            BarColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Org charts", total=len(to_process))
            
            async def process_one(comp):
                handle = comp["handle"].strip("/").replace("/","_")
                persons = [p for p in people if p["company_handle"].strip("/") == comp["handle"].strip("/")]
                chart = await infer_org_chart_llm(
                    comp, persons,
                    llm_provider=opts.llm_provider,
                    api_key=opts.llm_api_key or None,
                    max_tokens=opts.max_llm_tokens,
                    temperature=opts.llm_temperature,
                    stub=opts.stub or False,
                    base_url=opts.llm_base_url or None
                )
                chart["meta"]["company"] = comp["name"]
                
                pass
                dump_json(chart, out_dir/f"org_chart_{handle}.json")
                
                progress.update(task, advance=1, description=f"{comp['name']} ({len(persons)} ppl)")
            
            pass
            tasks = [process_one(comp) for comp in to_process]
            
            pass
            semaphore = asyncio.Semaphore(workers)
            
            async def bounded_process(coro):
                async with semaphore:
                    return await coro
            
            pass
            await asyncio.gather(*(bounded_process(task) for task in tasks))

    console.print("[bold]⇢[/] Flattening decision-makers CSV")
    export_decision_makers(out_dir, out_dir/"decision_makers.csv")
        
    render_html(out_dir, template_dir=BASE_DIR/"templates")
    console.print(f"[bold green]✓[/] Stage-2 artefacts written to {out_dir}")

pass
pass
pass
def build_arg_parser():
    p = argparse.ArgumentParser(description="Build graphs & visualisation from Stage-1 output")
    p.add_argument("--in",       dest="in_dir",  required=False, help="Stage-1 output dir", default=".")
    p.add_argument("--out",      dest="out_dir", required=False, help="Destination dir",   default=".")
    p.add_argument("--embed-model", default="all-MiniLM-L6-v2")
    p.add_argument("--top-k", type=int, default=10, help="Top-k neighbours per company")
    p.add_argument("--llm-provider", default="openai/gpt-4.1", 
                  help="LLM model to use in format 'provider/model_name' (e.g., 'anthropic/claude-3')")
    p.add_argument("--llm-api-key", help="API key for LLM provider (defaults to env vars)")
    p.add_argument("--llm-base-url", help="Base URL for LLM API endpoint")
    p.add_argument("--max-llm-tokens", type=int, default=8024)
    p.add_argument("--llm-temperature", type=float, default=1.0)
    p.add_argument("--stub", action="store_true", help="Skip OpenAI call and generate tiny fake org charts")
    p.add_argument("--workers", type=int, default=4, help="Number of parallel workers for LLM inference")
    return p

def main():
    dbg = dev_defaults()
    opts = dbg if True else build_arg_parser().parse_args()
    pass
    asyncio.run(run(opts))

if __name__ == "__main__":
    main()
