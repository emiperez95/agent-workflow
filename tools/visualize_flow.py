#!/usr/bin/env python3
"""
Flow Visualizer for Agent Invocations
Generates Mermaid diagrams and other visualizations from logged data
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
import argparse

# Setup paths
TOOLS_DIR = Path(__file__).parent
PROJECT_DIR = TOOLS_DIR.parent
LOGS_DIR = PROJECT_DIR / "logs"
DB_PATH = LOGS_DIR / "agent_workflow.db"

def generate_mermaid_flow(session_id):
    """Generate a Mermaid flow diagram for a session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT agent_name, phase, timestamp, status
        FROM agent_invocations
        WHERE session_id = ? AND agent_name != 'unknown'
        ORDER BY timestamp
    ''', (session_id,))
    
    invocations = cursor.fetchall()
    conn.close()
    
    if not invocations:
        print(f"No invocations found for session {session_id}")
        return None
    
    # Build Mermaid diagram
    diagram = ["graph TD"]
    
    # Group by phase
    phases = {}
    for agent, phase, timestamp, status in invocations:
        if phase not in phases:
            phases[phase] = []
        phases[phase].append((agent, status))
    
    # Create phase subgraphs
    node_id = 0
    phase_order = ['requirements', 'planning', 'development', 'review', 'finalization']
    
    for phase in phase_order:
        if phase in phases:
            diagram.append(f"    subgraph {phase.upper()}")
            for agent, status in phases[phase]:
                node_id += 1
                status_icon = "✓" if status == "completed" else "⚠"
                diagram.append(f"        A{node_id}[{agent} {status_icon}]")
            diagram.append("    end")
    
    # Add connections between sequential agents
    if len(invocations) > 1:
        diagram.append("    %% Connections")
        for i in range(len(invocations) - 1):
            diagram.append(f"    A{i+1} --> A{i+2}")
    
    return "\n".join(diagram)

def generate_gantt_chart(session_id):
    """Generate a Gantt chart showing parallel execution"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT agent_name, start_time, end_time
        FROM agent_invocations
        WHERE session_id = ? AND start_time IS NOT NULL AND end_time IS NOT NULL
        ORDER BY start_time
    ''', (session_id,))
    
    invocations = cursor.fetchall()
    conn.close()
    
    if not invocations:
        return None
    
    # Build Gantt chart in Mermaid format
    chart = ["gantt", "    title Agent Execution Timeline", "    dateFormat HH:mm:ss"]
    
    # Get session start time
    first_start = datetime.fromisoformat(invocations[0][1])
    
    # Add sections by phase
    current_section = None
    for agent, start, end in invocations:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        duration = (end_dt - start_dt).total_seconds()
        
        # Determine section
        if 'analyst' in agent or 'clarifier' in agent:
            section = "Requirements"
        elif 'planner' in agent or 'architect' in agent:
            section = "Planning"
        elif 'developer' in agent:
            section = "Development"
        elif 'reviewer' in agent or 'validator' in agent:
            section = "Review"
        else:
            section = "Finalization"
        
        if section != current_section:
            chart.append(f"    section {section}")
            current_section = section
        
        # Format time relative to session start
        start_offset = (start_dt - first_start).total_seconds()
        chart.append(f"    {agent}: {int(start_offset)}s, {int(duration)}s")
    
    return "\n".join(chart)

def generate_network_graph(min_connections=2):
    """Generate a network graph of agent interactions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Find agent pairs that frequently work together
    cursor.execute('''
        SELECT a1.agent_name, a2.agent_name, COUNT(*) as connection_count
        FROM agent_invocations a1
        JOIN agent_invocations a2 ON a1.session_id = a2.session_id
        WHERE a1.agent_name < a2.agent_name
          AND a1.agent_name != 'unknown'
          AND a2.agent_name != 'unknown'
          AND ABS(julianday(a1.timestamp) - julianday(a2.timestamp)) < 0.01  -- Within ~15 minutes
        GROUP BY a1.agent_name, a2.agent_name
        HAVING connection_count >= ?
        ORDER BY connection_count DESC
    ''', (min_connections,))
    
    connections = cursor.fetchall()
    conn.close()
    
    if not connections:
        return None
    
    # Build network graph in Mermaid format
    graph = ["graph LR"]
    
    # Add nodes with connections
    nodes = set()
    for agent1, agent2, count in connections:
        nodes.add(agent1)
        nodes.add(agent2)
        thickness = min(count, 5)  # Cap thickness at 5
        graph.append(f"    {agent1} ---|{count}| {agent2}")
    
    # Style nodes by type
    graph.append("    %% Styling")
    for node in nodes:
        if 'developer' in node:
            graph.append(f"    style {node} fill:#e1f5fe")
        elif 'reviewer' in node:
            graph.append(f"    style {node} fill:#fff3e0")
        elif 'analyst' in node or 'planner' in node:
            graph.append(f"    style {node} fill:#f3e5f5")
    
    return "\n".join(graph)

def save_visualization(content, filename):
    """Save visualization to file"""
    output_dir = PROJECT_DIR / "visualizations"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / filename
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"Saved visualization to {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description='Visualize agent workflow')
    parser.add_argument('--session', required=True, help='Session ID to visualize')
    parser.add_argument('--type', choices=['flow', 'gantt', 'network', 'all'], 
                       default='flow', help='Type of visualization')
    parser.add_argument('--output', help='Output filename (without extension)')
    args = parser.parse_args()
    
    if not DB_PATH.exists():
        print("No logs found. Run some agent workflows first!")
        return
    
    visualizations = []
    
    if args.type in ['flow', 'all']:
        flow = generate_mermaid_flow(args.session)
        if flow:
            print("\n📊 FLOW DIAGRAM")
            print("=" * 60)
            print(flow)
            print("\n" + "=" * 60)
            visualizations.append(('flow', flow))
    
    if args.type in ['gantt', 'all']:
        gantt = generate_gantt_chart(args.session)
        if gantt:
            print("\n⏱️  GANTT CHART")
            print("=" * 60)
            print(gantt)
            print("\n" + "=" * 60)
            visualizations.append(('gantt', gantt))
    
    if args.type in ['network', 'all']:
        network = generate_network_graph()
        if network:
            print("\n🔗 NETWORK GRAPH")
            print("=" * 60)
            print(network)
            print("\n" + "=" * 60)
            visualizations.append(('network', network))
    
    # Save visualizations
    if args.output and visualizations:
        for viz_type, content in visualizations:
            filename = f"{args.output}_{viz_type}.md"
            save_visualization(f"```mermaid\n{content}\n```", filename)
    
    print("\n💡 TIP: Copy the Mermaid code above and paste into:")
    print("   - GitHub README.md files")
    print("   - mermaid.live online editor")
    print("   - Any Markdown editor with Mermaid support")

if __name__ == "__main__":
    main()