# CPU Usage with Agent Invocation Annotations

## How to Use This Panel

The `cpu-with-agents-panel.json` combines CPU usage monitoring with agent invocation markers to help correlate system performance with agent activity.

### Features:
- **CPU Usage**: Stacked area chart showing system, user, I/O wait, and idle time
- **Agent Markers**: Vertical lines/points showing when each agent was invoked
- **Tooltips**: Hover over markers to see which agent was running

### To Add to Your Dashboard:

1. **Option 1: Import the Panel**
   - Copy the contents of `cpu-with-agents-panel.json`
   - In Grafana, edit your dashboard
   - Add Panel → Import Panel from JSON
   - Paste the JSON

2. **Option 2: Add Annotations to Existing Panel**
   
   Add this annotation query to your existing CPU panel:

   ```json
   "annotations": {
     "list": [
       {
         "datasource": {
           "type": "prometheus",
           "uid": "${datasource}"
         },
         "enable": true,
         "expr": "increase(agent_invocation_total[1m]) > 0",
         "iconColor": "red",
         "name": "Agent Started",
         "titleFormat": "Agent: {{agent_name}}",
         "textFormat": "{{agent_name}} ({{phase}})",
         "tags": ["agent_name", "phase"]
       }
     ]
   }
   ```

### Alternative Queries for Different Views:

#### 1. Show Only Specific Agents
```promql
increase(agent_invocation_total{agent_name=~"backend-developer|frontend-developer"}[1m]) > 0
```

#### 2. Show Only Heavy Agents (>60s duration)
```promql
increase(agent_duration_seconds_count{agent_name=~".*"}[1m]) * 
(avg by (agent_name) (rate(agent_duration_seconds_sum[5m]) / rate(agent_duration_seconds_count[5m])) > 60)
```

#### 3. Show Failed Agents Only
```promql
increase(agent_error_total[1m]) > 0
```

### Visual Correlation Tips:

1. **CPU Spikes**: Look for agent invocations that align with CPU usage increases
2. **I/O Wait**: Database and file-heavy agents (like `context-analyzer`) may cause I/O wait
3. **User CPU**: Compute-intensive agents will show in user CPU time
4. **System CPU**: Agents doing file operations will increase system CPU

### Adding Duration Bars:

To show agent execution duration as horizontal bars instead of just start points:

```json
{
  "expr": "agent_duration_seconds_sum / agent_duration_seconds_count",
  "legendFormat": "{{agent_name}} duration",
  "format": "time_series"
}
```

### Color Mapping by Phase:

The panel includes phase-based coloring:
- **Blue**: Requirements phase agents
- **Purple**: Planning phase agents  
- **Green**: Development phase agents
- **Yellow**: Review phase agents
- **Orange**: Finalization phase agents

### Troubleshooting:

If annotations don't appear:
1. Ensure the agent workflow exporter is running (`python3 tools/prometheus_exporter.py`)
2. Check that Prometheus is scraping the metrics
3. Verify time range includes agent invocations
4. Try this test query in Prometheus: `agent_invocation_total`

### Combined Dashboard Example:

For a complete performance analysis dashboard, combine:
1. This CPU + Agents panel
2. Memory usage panel with agent annotations
3. Disk I/O panel with agent annotations
4. Network traffic panel with agent annotations

This creates a comprehensive view of how different agents impact system resources.