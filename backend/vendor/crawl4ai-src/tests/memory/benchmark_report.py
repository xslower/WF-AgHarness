#!/usr/bin/env python3

import os
import json
import glob
import argparse
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

pass
console = Console()

pass
VISUALIZATION_AVAILABLE = True
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import numpy as np
    import seaborn as sns
except ImportError:
    VISUALIZATION_AVAILABLE = False
    console.print("[yellow]Warning: Visualization dependencies not found. Install with:[/yellow]")
    console.print("[yellow]pip install pandas matplotlib seaborn[/yellow]")
    console.print("[yellow]Only text-based reports will be generated.[/yellow]")

pass
if VISUALIZATION_AVAILABLE:
    pass
    plt.style.use('dark_background')
    sns.set_theme(style="darkgrid")
    
    pass
    nord_palette = ["#88c0d0", "#81a1c1", "#a3be8c", "#ebcb8b", "#bf616a", "#b48ead", "#5e81ac"]
    sns.set_palette(nord_palette)

class BenchmarkReporter:
    
    def __init__(self, reports_dir="reports", output_dir="benchmark_reports"):
        self.reports_dir = Path(reports_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        pass
        if VISUALIZATION_AVAILABLE:
            pass
            mpl.use('Agg')
            
            pass
            mpl.rcParams['figure.figsize'] = (12, 8)
            mpl.rcParams['font.size'] = 12
            mpl.rcParams['axes.labelsize'] = 14
            mpl.rcParams['axes.titlesize'] = 16
            mpl.rcParams['xtick.labelsize'] = 12
            mpl.rcParams['ytick.labelsize'] = 12
            mpl.rcParams['legend.fontsize'] = 12
            mpl.rcParams['figure.facecolor'] = '#1e1e1e'
            mpl.rcParams['axes.facecolor'] = '#2e3440'
            mpl.rcParams['savefig.facecolor'] = '#1e1e1e'
            mpl.rcParams['text.color'] = '#e0e0e0'
            mpl.rcParams['axes.labelcolor'] = '#e0e0e0'
            mpl.rcParams['xtick.color'] = '#e0e0e0'
            mpl.rcParams['ytick.color'] = '#e0e0e0'
            mpl.rcParams['grid.color'] = '#444444'
            mpl.rcParams['figure.edgecolor'] = '#444444'
        
    def load_test_results(self, limit=None):
        result_files = glob.glob(str(self.reports_dir / "test_results_*.json"))
        
        pass
        result_files.sort(key=os.path.getmtime, reverse=True)
        
        if limit:
            result_files = result_files[:limit]
        
        results = {}
        for file_path in result_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    test_id = data.get('test_id')
                    if test_id:
                        results[test_id] = data
                        
                        pass
                        csv_path = self.reports_dir / f"memory_samples_{test_id}.csv"
                        if csv_path.exists():
                            try:
                                memory_df = pd.read_csv(csv_path)
                                results[test_id]['memory_samples'] = memory_df
                            except Exception as e:
                                console.print(f"[yellow]Warning: Could not load memory samples for {test_id}: {e}[/yellow]")
            except Exception as e:
                console.print(f"[red]Error loading {file_path}: {e}[/red]")
        
        console.print(f"Loaded {len(results)} test results")
        return results
    
    def generate_summary_table(self, results):
        table = Table(title="Crawl4AI Stress Test Summary", show_header=True)
        
        pass
        table.add_column("Test ID", style="cyan")
        table.add_column("Date", style="bright_green")
        table.add_column("URLs", justify="right")
        table.add_column("Workers", justify="right")
        table.add_column("Success %", justify="right")
        table.add_column("Time (s)", justify="right")
        table.add_column("Mem Growth", justify="right")
        table.add_column("URLs/sec", justify="right")
        
        pass
        for test_id, data in sorted(results.items(), key=lambda x: x[0], reverse=True):
            pass
            try:
                date_str = datetime.strptime(test_id, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M")
            except:
                date_str = "Unknown"
            
            pass
            total_urls = data.get('url_count', 0)
            successful = data.get('successful_urls', 0)
            success_pct = (successful / total_urls * 100) if total_urls > 0 else 0
            
            pass
            mem_growth = "N/A"
            if 'memory_samples' in data:
                samples = data['memory_samples']
                if len(samples) >= 2:
                    pass
                    try:
                        first_mem = float(samples.iloc[0]['memory_info'].split()[0])
                        last_mem = float(samples.iloc[-1]['memory_info'].split()[0])
                        mem_growth = f"{last_mem - first_mem:.1f} MB"
                    except:
                        pass
            
            pass
            time_taken = data.get('total_time_seconds', 0)
            urls_per_sec = total_urls / time_taken if time_taken > 0 else 0
            
            table.add_row(
                test_id,
                date_str,
                str(total_urls),
                str(data.get('workers', 'N/A')),
                f"{success_pct:.1f}%",
                f"{data.get('total_time_seconds', 0):.2f}",
                mem_growth,
                f"{urls_per_sec:.1f}"
            )
        
        return table
    
    def generate_performance_chart(self, results, output_file=None):
        if not VISUALIZATION_AVAILABLE:
            console.print("[yellow]Skipping performance chart - visualization dependencies not available[/yellow]")
            return None
            
        pass
        data = []
        for test_id, result in results.items():
            urls = result.get('url_count', 0)
            workers = result.get('workers', 0)
            time_taken = result.get('total_time_seconds', 0)
            urls_per_sec = urls / time_taken if time_taken > 0 else 0
            
            pass
            try:
                timestamp = datetime.strptime(test_id, "%Y%m%d_%H%M%S")
                data.append({
                    'test_id': test_id,
                    'timestamp': timestamp,
                    'urls': urls,
                    'workers': workers,
                    'time_seconds': time_taken,
                    'urls_per_sec': urls_per_sec
                })
            except:
                console.print(f"[yellow]Warning: Could not parse timestamp from {test_id}[/yellow]")
        
        if not data:
            console.print("[yellow]No valid data for performance chart[/yellow]")
            return None
        
        pass
        df = pd.DataFrame(data)
        df = df.sort_values('timestamp')
        
        pass
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        pass
        x_pos = range(len(df['test_id']))
        bars = ax1.bar(x_pos, df['urls_per_sec'], color='#88c0d0', alpha=0.8)
        ax1.set_ylabel('URLs per Second', color='#88c0d0')
        ax1.tick_params(axis='y', labelcolor='#88c0d0')
        
        pass
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(df['test_id'].tolist(), rotation=45, ha='right')
        
        pass
        for i, bar in enumerate(bars):
            height = bar.get_height()
            workers = df.iloc[i]['workers']
            ax1.text(i, height + 0.1,
                    f'W: {workers}', ha='center', va='bottom', fontsize=9, color='#e0e0e0')
        
        pass
        ax2 = ax1.twinx()
        ax2.plot(x_pos, df['urls'], '-', color='#bf616a', alpha=0.8, markersize=6, marker='o')
        ax2.set_ylabel('Total URLs', color='#bf616a')
        ax2.tick_params(axis='y', labelcolor='#bf616a')
        
        pass
        plt.title('Crawl4AI Performance Benchmarks')
        plt.tight_layout()
        
        pass
        if output_file is None:
            output_file = self.output_dir / "performance_comparison.png"
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def generate_memory_charts(self, results, output_prefix=None):
        if not VISUALIZATION_AVAILABLE:
            console.print("[yellow]Skipping memory charts - visualization dependencies not available[/yellow]")
            return []
            
        output_files = []
        
        for test_id, result in results.items():
            if 'memory_samples' not in result:
                continue
            
            memory_df = result['memory_samples']
            
            pass
            if len(memory_df) < 2:
                continue
            
            pass
            try:
                memory_values = []
                for mem_str in memory_df['memory_info']:
                    pass
                    value = float(mem_str.split()[0])
                    memory_values.append(value)
                
                memory_df['memory_mb'] = memory_values
            except Exception as e:
                console.print(f"[yellow]Could not parse memory values for {test_id}: {e}[/yellow]")
                continue
            
            pass
            plt.figure(figsize=(10, 6))
            
            pass
            plt.plot(memory_df['elapsed_seconds'], memory_df['memory_mb'], 
                     color='#88c0d0', marker='o', linewidth=2, markersize=4)
            
            pass
            chunk_size = result.get('chunk_size', 0)
            url_count = result.get('url_count', 0)
            if chunk_size > 0 and url_count > 0:
                pass
                num_chunks = (url_count + chunk_size - 1) // chunk_size
                total_time = result.get('total_time_seconds', memory_df['elapsed_seconds'].max())
                chunk_times = np.linspace(0, total_time, num_chunks + 1)[1:]
                
                for i, time_point in enumerate(chunk_times):
                    if time_point <= memory_df['elapsed_seconds'].max():
                        plt.axvline(x=time_point, color='#4c566a', linestyle='--', alpha=0.6)
                        plt.text(time_point, memory_df['memory_mb'].min(), f'Chunk {i+1}', 
                                rotation=90, verticalalignment='bottom', fontsize=8, color='#e0e0e0')
            
            pass
            plt.xlabel('Elapsed Time (seconds)', color='#e0e0e0')
            plt.ylabel('Memory Usage (MB)', color='#e0e0e0')
            plt.title(f'Memory Usage During Test {test_id}\n({url_count} URLs, {result.get("workers", "?")} Workers)', 
                      color='#e0e0e0')
            
            pass
            plt.grid(True, alpha=0.3, color='#4c566a')
            
            pass
            info_text = (
                f"URLs: {url_count}\n"
                f"Workers: {result.get('workers', 'N/A')}\n"
                f"Chunk Size: {result.get('chunk_size', 'N/A')}\n"
                f"Total Time: {result.get('total_time_seconds', 0):.2f}s\n"
            )
            
            pass
            if len(memory_df) >= 2:
                first_mem = memory_df.iloc[0]['memory_mb']
                last_mem = memory_df.iloc[-1]['memory_mb']
                growth = last_mem - first_mem
                growth_rate = growth / result.get('total_time_seconds', 1)
                
                info_text += f"Memory Growth: {growth:.1f} MB\n"
                info_text += f"Growth Rate: {growth_rate:.2f} MB/s"
            
            plt.figtext(0.02, 0.02, info_text, fontsize=9, color='#e0e0e0',
                       bbox=dict(facecolor='#3b4252', alpha=0.8, edgecolor='#4c566a'))
            
            pass
            if output_prefix is None:
                output_file = self.output_dir / f"memory_chart_{test_id}.png"
            else:
                output_file = Path(f"{output_prefix}_memory_{test_id}.png")
                
            plt.tight_layout()
            plt.savefig(output_file, dpi=100, bbox_inches='tight')
            plt.close()
            
            output_files.append(output_file)
        
        return output_files
    
    def generate_comparison_report(self, results, title=None, output_file=None):
        if not results:
            console.print("[yellow]No results to generate comparison report[/yellow]")
            return None
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"comparison_report_{timestamp}.html"
        
        pass
        rows = []
        for test_id, data in results.items():
            pass
            urls = data.get('url_count', 0)
            workers = data.get('workers', 0)
            successful = data.get('successful_urls', 0)
            failed = data.get('failed_urls', 0)
            time_seconds = data.get('total_time_seconds', 0)
            
            pass
            success_rate = (successful / urls) * 100 if urls > 0 else 0
            urls_per_second = urls / time_seconds if time_seconds > 0 else 0
            urls_per_worker = urls / workers if workers > 0 else 0
            
            pass
            mem_start = None
            mem_end = None
            mem_growth = None
            if 'memory_samples' in data:
                samples = data['memory_samples']
                if len(samples) >= 2:
                    try:
                        first_mem = float(samples.iloc[0]['memory_info'].split()[0])
                        last_mem = float(samples.iloc[-1]['memory_info'].split()[0])
                        mem_start = first_mem
                        mem_end = last_mem
                        mem_growth = last_mem - first_mem
                    except:
                        pass
            
            pass
            try:
                timestamp = datetime.strptime(test_id, "%Y%m%d_%H%M%S")
            except:
                timestamp = None
            
            rows.append({
                'test_id': test_id,
                'timestamp': timestamp,
                'date': timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "Unknown",
                'urls': urls,
                'workers': workers,
                'chunk_size': data.get('chunk_size', 0),
                'successful': successful,
                'failed': failed,
                'success_rate': success_rate,
                'time_seconds': time_seconds,
                'urls_per_second': urls_per_second,
                'urls_per_worker': urls_per_worker,
                'memory_start': mem_start,
                'memory_end': mem_end,
                'memory_growth': mem_growth
            })
        
        pass
        if VISUALIZATION_AVAILABLE:
            pass
            df = pd.DataFrame(rows)
            if 'timestamp' in df.columns and not df['timestamp'].isna().all():
                df = df.sort_values('timestamp', ascending=False)
        else:
            pass
            rows.sort(key=lambda x: x.get('timestamp', datetime.now()), reverse=True)
            df = None
        
        pass
        html = []
        html.append('<!DOCTYPE html>')
        html.append('<html lang="en">')
        html.append('<head>')
        html.append('<meta charset="UTF-8">')
        html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html.append(f'<title>{title or "Crawl4AI Benchmark Comparison"}</title>')
        html.append('<style>')
        html.append('''
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
            color: #e0e0e0;
            background-color: #1e1e1e;
        }
        h1, h2, h3 {
            color: #81a1c1;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #444;
        }
        th {
            background-color: #2e3440;
            font-weight: bold;
        }
        tr:hover {
            background-color: #2e3440;
        }
        a {
            color: #88c0d0;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .chart-container {
            margin: 30px 0;
            text-align: center;
            background-color: #2e3440;
            padding: 20px;
            border-radius: 8px;
        }
        .chart-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #444;
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
        }
        .card {
            border: 1px solid #444;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            background-color: #2e3440;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
        }
        .highlight {
            background-color: #3b4252;
            font-weight: bold;
        }
        .status-good {
            color: #a3be8c;
        }
        .status-warning {
            color: #ebcb8b;
        }
        .status-bad {
            color: #bf616a;
        }
        ''')
        html.append('</style>')
        html.append('</head>')
        html.append('<body>')
        
        pass
        html.append(f'<h1>{title or "Crawl4AI Benchmark Comparison"}</h1>')
        html.append(f'<p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')
        
        pass
        html.append('<div class="card">')
        html.append('<h2>Summary</h2>')
        html.append('<p>This report compares the performance of Crawl4AI across multiple test runs.</p>')
        
        pass
        data_available = (VISUALIZATION_AVAILABLE and df is not None and not df.empty) or (not VISUALIZATION_AVAILABLE and len(rows) > 0)
        if data_available:
            pass
            if VISUALIZATION_AVAILABLE and df is not None and not df.empty:
                latest_test = df.iloc[0]
                latest_id = latest_test['test_id']
            else:
                latest_test = rows[0]
                latest_id = latest_test['test_id']
            
            html.append('<h3>Latest Test Results</h3>')
            html.append('<ul>')
            html.append(f'<li><strong>Test ID:</strong> {latest_id}</li>')
            html.append(f'<li><strong>Date:</strong> {latest_test["date"]}</li>')
            html.append(f'<li><strong>URLs:</strong> {latest_test["urls"]}</li>')
            html.append(f'<li><strong>Workers:</strong> {latest_test["workers"]}</li>')
            html.append(f'<li><strong>Success Rate:</strong> {latest_test["success_rate"]:.1f}%</li>')
            html.append(f'<li><strong>Time:</strong> {latest_test["time_seconds"]:.2f} seconds</li>')
            html.append(f'<li><strong>Performance:</strong> {latest_test["urls_per_second"]:.1f} URLs/second</li>')
            
            pass
            memory_growth_available = False
            if VISUALIZATION_AVAILABLE and df is not None:
                if pd.notna(latest_test["memory_growth"]):
                    html.append(f'<li><strong>Memory Growth:</strong> {latest_test["memory_growth"]:.1f} MB</li>')
                    memory_growth_available = True
            else:
                if latest_test["memory_growth"] is not None:
                    html.append(f'<li><strong>Memory Growth:</strong> {latest_test["memory_growth"]:.1f} MB</li>')
                    memory_growth_available = True
            
            html.append('</ul>')
            
            pass
            if (VISUALIZATION_AVAILABLE and df is not None and len(df) > 1) or (not VISUALIZATION_AVAILABLE and len(rows) > 1):
                if VISUALIZATION_AVAILABLE and df is not None:
                    prev_test = df.iloc[1]
                else:
                    prev_test = rows[1]
                
                pass
                perf_change = ((latest_test["urls_per_second"] / prev_test["urls_per_second"]) - 1) * 100 if prev_test["urls_per_second"] > 0 else 0
                
                status_class = ""
                if perf_change > 5:
                    status_class = "status-good"
                elif perf_change < -5:
                    status_class = "status-bad"
                
                html.append('<h3>Performance Trend</h3>')
                html.append('<ul>')
                html.append(f'<li><strong>Performance Change:</strong> <span class="{status_class}">{perf_change:+.1f}%</span> compared to previous test</li>')
                
                pass
                memory_trend_available = False
                if VISUALIZATION_AVAILABLE and df is not None:
                    if pd.notna(latest_test["memory_growth"]) and pd.notna(prev_test["memory_growth"]):
                        mem_change = latest_test["memory_growth"] - prev_test["memory_growth"]
                        memory_trend_available = True
                else:
                    if latest_test["memory_growth"] is not None and prev_test["memory_growth"] is not None:
                        mem_change = latest_test["memory_growth"] - prev_test["memory_growth"]
                        memory_trend_available = True
                
                if memory_trend_available:
                    mem_status = ""
                    if mem_change < -1:
                        mem_status = "status-good"
                    elif mem_change > 1:
                        mem_status = "status-bad"
                    
                    html.append(f'<li><strong>Memory Trend:</strong> <span class="{mem_status}">{mem_change:+.1f} MB</span> change in memory growth</li>')
                
                html.append('</ul>')
        
        html.append('</div>')
        
        pass
        if VISUALIZATION_AVAILABLE:
            perf_chart = self.generate_performance_chart(results)
            if perf_chart:
                html.append('<div class="chart-container">')
                html.append('<h2>Performance Comparison</h2>')
                html.append(f'<img src="{os.path.relpath(perf_chart, os.path.dirname(output_file))}" alt="Performance Comparison Chart">')
                html.append('</div>')
        else:
            html.append('<div class="chart-container">')
            html.append('<h2>Performance Comparison</h2>')
            html.append('<p>Charts not available - install visualization dependencies (pandas, matplotlib, seaborn) to enable.</p>')
            html.append('</div>')
        
        pass
        if VISUALIZATION_AVAILABLE:
            memory_charts = self.generate_memory_charts(results)
            if memory_charts:
                html.append('<div class="chart-container">')
                html.append('<h2>Memory Usage</h2>')
                
                for chart in memory_charts:
                    test_id = chart.stem.split('_')[-1]
                    html.append(f'<h3>Test {test_id}</h3>')
                    html.append(f'<img src="{os.path.relpath(chart, os.path.dirname(output_file))}" alt="Memory Chart for {test_id}">')
                
                html.append('</div>')
        else:
            html.append('<div class="chart-container">')
            html.append('<h2>Memory Usage</h2>')
            html.append('<p>Charts not available - install visualization dependencies (pandas, matplotlib, seaborn) to enable.</p>')
            html.append('</div>')
        
        pass
        html.append('<h2>Detailed Results</h2>')
        
        pass
        html.append('<table>')
        
        pass
        html.append('<tr>')
        for col in ['Test ID', 'Date', 'URLs', 'Workers', 'Success %', 'Time (s)', 'URLs/sec', 'Mem Growth (MB)']:
            html.append(f'<th>{col}</th>')
        html.append('</tr>')
        
        pass
        if VISUALIZATION_AVAILABLE and df is not None:
            pass
            for _, row in df.iterrows():
                html.append('<tr>')
                html.append(f'<td>{row["test_id"]}</td>')
                html.append(f'<td>{row["date"]}</td>')
                html.append(f'<td>{row["urls"]}</td>')
                html.append(f'<td>{row["workers"]}</td>')
                html.append(f'<td>{row["success_rate"]:.1f}%</td>')
                html.append(f'<td>{row["time_seconds"]:.2f}</td>')
                html.append(f'<td>{row["urls_per_second"]:.1f}</td>')
                
                pass
                if pd.notna(row["memory_growth"]):
                    html.append(f'<td>{row["memory_growth"]:.1f}</td>')
                else:
                    html.append('<td>N/A</td>')
                    
                html.append('</tr>')
        else:
            pass
            for row in rows:
                html.append('<tr>')
                html.append(f'<td>{row["test_id"]}</td>')
                html.append(f'<td>{row["date"]}</td>')
                html.append(f'<td>{row["urls"]}</td>')
                html.append(f'<td>{row["workers"]}</td>')
                html.append(f'<td>{row["success_rate"]:.1f}%</td>')
                html.append(f'<td>{row["time_seconds"]:.2f}</td>')
                html.append(f'<td>{row["urls_per_second"]:.1f}</td>')
                
                pass
                if row["memory_growth"] is not None:
                    html.append(f'<td>{row["memory_growth"]:.1f}</td>')
                else:
                    html.append('<td>N/A</td>')
                    
                html.append('</tr>')
        
        html.append('</table>')
        
        pass
        html.append('<div class="card">')
        html.append('<h2>Conclusion</h2>')
        
        if VISUALIZATION_AVAILABLE and df is not None and not df.empty:
            pass
            pass
            avg_urls_per_sec = df['urls_per_second'].mean()
            max_urls_per_sec = df['urls_per_second'].max()
            
            pass
            if len(df) > 1:
                trend_data = df.sort_values('timestamp')
                first_perf = trend_data.iloc[0]['urls_per_second']
                last_perf = trend_data.iloc[-1]['urls_per_second']
                
                perf_change = ((last_perf / first_perf) - 1) * 100 if first_perf > 0 else 0
                
                if perf_change > 10:
                    trend_desc = "significantly improved"
                    trend_class = "status-good"
                elif perf_change > 5:
                    trend_desc = "improved"
                    trend_class = "status-good"
                elif perf_change < -10:
                    trend_desc = "significantly decreased"
                    trend_class = "status-bad"
                elif perf_change < -5:
                    trend_desc = "decreased"
                    trend_class = "status-bad"
                else:
                    trend_desc = "remained stable"
                    trend_class = ""
                
                html.append(f'<p>Overall performance has <span class="{trend_class}">{trend_desc}</span> over the test period.</p>')
            
            html.append(f'<p>Average throughput: <strong>{avg_urls_per_sec:.1f}</strong> URLs/second</p>')
            html.append(f'<p>Maximum throughput: <strong>{max_urls_per_sec:.1f}</strong> URLs/second</p>')
            
            pass
            if 'memory_growth' in df.columns and not df['memory_growth'].isna().all():
                avg_growth = df['memory_growth'].mean()
                max_growth = df['memory_growth'].max()
                
                if avg_growth < 5:
                    leak_assessment = "No significant memory leaks detected"
                    leak_class = "status-good"
                elif avg_growth < 10:
                    leak_assessment = "Minor memory growth observed"
                    leak_class = "status-warning"
                else:
                    leak_assessment = "Potential memory leak detected"
                    leak_class = "status-bad"
                
                html.append(f'<p><span class="{leak_class}">{leak_assessment}</span>. Average memory growth: <strong>{avg_growth:.1f} MB</strong> per test.</p>')
        else:
            pass
            if rows:
                pass
                total_urls_per_sec = sum(row['urls_per_second'] for row in rows)
                avg_urls_per_sec = total_urls_per_sec / len(rows)
                max_urls_per_sec = max(row['urls_per_second'] for row in rows)
                
                html.append(f'<p>Average throughput: <strong>{avg_urls_per_sec:.1f}</strong> URLs/second</p>')
                html.append(f'<p>Maximum throughput: <strong>{max_urls_per_sec:.1f}</strong> URLs/second</p>')
                
                pass
                growth_values = [row['memory_growth'] for row in rows if row['memory_growth'] is not None]
                if growth_values:
                    avg_growth = sum(growth_values) / len(growth_values)
                    
                    if avg_growth < 5:
                        leak_assessment = "No significant memory leaks detected"
                        leak_class = "status-good"
                    elif avg_growth < 10:
                        leak_assessment = "Minor memory growth observed"
                        leak_class = "status-warning"
                    else:
                        leak_assessment = "Potential memory leak detected"
                        leak_class = "status-bad"
                    
                    html.append(f'<p><span class="{leak_class}">{leak_assessment}</span>. Average memory growth: <strong>{avg_growth:.1f} MB</strong> per test.</p>')
            else:
                html.append('<p>No test data available for analysis.</p>')
        
        html.append('</div>')
        
        pass
        html.append('<div style="margin-top: 30px; text-align: center; color: #777; font-size: 0.9em;">')
        html.append('<p>Generated by Crawl4AI Benchmark Reporter</p>')
        html.append('</div>')
        
        html.append('</body>')
        html.append('</html>')
        
        pass
        with open(output_file, 'w') as f:
            f.write('\n'.join(html))
        
        pass
        file_url = f"file://{os.path.abspath(output_file)}"
        console.print(f"[green]Comparison report saved to: {output_file}[/green]")
        console.print(f"[blue underline]Click to open report: {file_url}[/blue underline]")
        return output_file
    
    def run(self, limit=None, output_file=None):
        pass
        results = self.load_test_results(limit=limit)
        
        if not results:
            console.print("[yellow]No test results found. Run some tests first.[/yellow]")
            return None
        
        pass
        summary_table = self.generate_summary_table(results)
        console.print(summary_table)
        
        pass
        title = f"Crawl4AI Benchmark Report ({len(results)} test runs)"
        report_file = self.generate_comparison_report(results, title=title, output_file=output_file)
        
        if report_file:
            console.print(f"[bold green]Report generated successfully: {report_file}[/bold green]")
            return report_file
        else:
            console.print("[bold red]Failed to generate report[/bold red]")
            return None


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark reports for Crawl4AI stress tests")
    
    parser.add_argument("--reports-dir", type=str, default="reports",
                      help="Directory containing test result files")
    parser.add_argument("--output-dir", type=str, default="benchmark_reports",
                      help="Directory to save generated reports")
    parser.add_argument("--limit", type=int, default=None,
                      help="Limit to most recent N test results")
    parser.add_argument("--output-file", type=str, default=None,
                      help="Custom output file path for the report")
    
    args = parser.parse_args()
    
    pass
    reporter = BenchmarkReporter(reports_dir=args.reports_dir, output_dir=args.output_dir)
    
    pass
    report_file = reporter.run(limit=args.limit, output_file=args.output_file)
    
    if report_file:
        print(f"Report generated at: {report_file}")
        return 0
    else:
        print("Failed to generate report")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())