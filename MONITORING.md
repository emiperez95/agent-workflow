# Monitoring with Prometheus and Grafana

This guide explains how to set up Prometheus and Grafana monitoring for the Claude Development Pipeline agent workflow metrics.

## Overview

The monitoring system tracks:
- Agent invocation counts and rates
- Execution duration metrics (with percentiles)
- Success/failure rates
- Phase distribution
- Parallel execution patterns
- Session metrics
- Database statistics

## Prerequisites

1. **Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Prometheus** installed ([Download](https://prometheus.io/download/))
3. **Grafana** installed ([Download](https://grafana.com/grafana/download))

## Quick Start

### 1. Start the Prometheus Exporter

```bash
# Start the exporter (default port: 9090)
python3 tools/prometheus_exporter.py

# Or with custom options
python3 tools/prometheus_exporter.py --port 9091 --interval 10
```

The exporter will:
- Connect to the SQLite database at `logs/agent_workflow.db`
- Expose metrics at `http://localhost:9090/metrics`
- Update metrics every 15 seconds (configurable)

### 2. Configure Prometheus

1. Copy or merge the provided configuration:
   ```bash
   # If Prometheus is installed via Homebrew (macOS)
   cp config/prometheus.yml /usr/local/etc/prometheus/prometheus.yml
   
   # Or specify config when starting Prometheus
   prometheus --config.file=config/prometheus.yml
   ```

2. Start Prometheus:
   ```bash
   prometheus --config.file=config/prometheus.yml
   ```

3. Verify at `http://localhost:9090/targets` that the `agent_workflow` target is UP

### 3. Import Grafana Dashboard

1. Access Grafana at `http://localhost:3000` (default credentials: admin/admin)

2. Add Prometheus data source:
   - Navigate to Configuration → Data Sources
   - Add New Data Source → Prometheus
   - URL: `http://localhost:9090`
   - Save & Test

3. Import the dashboard:
   - Navigate to Dashboards → Import
   - Upload `config/grafana-dashboard.json`
   - Select your Prometheus datasource
   - Import

## Available Metrics

### Counter Metrics
- `agent_invocation_total`: Total invocations by agent, phase, status, model
- `agent_error_total`: Total errors by agent and phase
- `phase_distribution_total`: Distribution across workflow phases

### Histogram Metrics
- `agent_duration_seconds`: Execution duration with percentiles
- `session_duration_seconds`: Session duration distribution

### Gauge Metrics
- `agent_last_execution_timestamp`: Last execution time per agent
- `agent_success_rate`: Success rate percentage per agent
- `active_sessions_count`: Currently active sessions
- `parallel_executions_current`: Current parallel executions
- `total_unique_agents`: Total unique agents in system
- `total_sessions`: Total logged sessions
- `avg_agents_per_session`: Average agents per session

### Info Metrics
- `agent_workflow_database_info`: Database metadata

## Dashboard Panels

The provided Grafana dashboard includes:

1. **Overview Stats**: Total invocations, unique agents, sessions, success rate
2. **Agent Performance Timeline**: 95th percentile execution times
3. **Agent Performance Table**: Invocation counts and success rates
4. **Phase Distribution**: Donut chart of workflow phases
5. **Average Execution Time**: Bar chart by agent
6. **Agent Invocation Rate**: Time series of invocation rates
7. **System Metrics**: Parallel executions, active sessions, avg agents/session

## Prometheus Queries

Useful PromQL queries for custom panels:

```promql
# Top 5 slowest agents (95th percentile)
topk(5, histogram_quantile(0.95, rate(agent_duration_seconds_bucket[5m])))

# Agents with declining success rate
agent_success_rate < 80

# Phase distribution percentage
sum by (phase) (phase_distribution_total) / sum(phase_distribution_total) * 100

# Parallel execution efficiency
parallel_executions_current / active_sessions_count

# Error rate by agent (last 5 minutes)
rate(agent_error_total[5m])

# Session completion rate
rate(session_duration_seconds_count[1h])
```

## Alert Rules

Create `agent_workflow_rules.yml` for alerting:

```yaml
groups:
  - name: agent_workflow_alerts
    interval: 30s
    rules:
      - alert: AgentExecutionSlow
        expr: histogram_quantile(0.95, rate(agent_duration_seconds_bucket[5m])) > 300
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Agent {{ $labels.agent_name }} is slow"
          description: "95th percentile > 5 minutes"
      
      - alert: HighErrorRate
        expr: rate(agent_error_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate for {{ $labels.agent_name }}"
      
      - alert: LowSuccessRate
        expr: agent_success_rate < 70
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low success rate for {{ $labels.agent_name }}"
```

## Running as a Service

### systemd (Linux)

Create `/etc/systemd/system/agent-workflow-exporter.service`:

```ini
[Unit]
Description=Agent Workflow Prometheus Exporter
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/agent-workflow
ExecStart=/usr/bin/python3 /path/to/agent-workflow/tools/prometheus_exporter.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable agent-workflow-exporter
sudo systemctl start agent-workflow-exporter
```

### launchd (macOS)

Create `~/Library/LaunchAgents/com.agent-workflow.exporter.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agent-workflow.exporter</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/agent-workflow/tools/prometheus_exporter.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/agent-workflow-exporter.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/agent-workflow-exporter.out</string>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.agent-workflow.exporter.plist
```

## Troubleshooting

### Exporter Issues

1. **Database not found**:
   - Ensure `logs/agent_workflow.db` exists
   - Run an agent workflow to create the database

2. **Port already in use**:
   - Use a different port: `--port 9091`
   - Check what's using the port: `lsof -i :9090`

3. **No metrics appearing**:
   - Check exporter logs for errors
   - Verify database has data: `sqlite3 logs/agent_workflow.db "SELECT COUNT(*) FROM agent_invocations"`

### Prometheus Issues

1. **Target DOWN in Prometheus**:
   - Check exporter is running
   - Verify network connectivity
   - Check Prometheus logs

2. **No data in queries**:
   - Wait for scrape interval (15s)
   - Check metric names match
   - Verify time range in query

### Grafana Issues

1. **No data in dashboard**:
   - Verify Prometheus datasource is working
   - Check time range selector
   - Refresh dashboard (F5)

2. **Panels showing errors**:
   - Check datasource variable is set
   - Verify metrics exist in Prometheus
   - Check panel query syntax

## Advanced Configuration

### Custom Metrics

To add custom metrics, edit `tools/prometheus_exporter.py`:

```python
# Add new metric
custom_metric = Gauge(
    'custom_metric_name',
    'Description of metric',
    ['label1', 'label2'],
    registry=registry
)

# In _collect_custom_metrics method
custom_metric.labels(label1='value1', label2='value2').set(42)
```

### Performance Tuning

For large databases or high-frequency updates:

1. Increase update interval: `--interval 30`
2. Add database indexes for frequently queried columns
3. Use connection pooling in the exporter
4. Consider using PostgreSQL instead of SQLite

### Multi-Instance Setup

To monitor multiple projects:

1. Run exporters on different ports
2. Add multiple targets in Prometheus config
3. Use instance labels to distinguish in Grafana

## Integration with CI/CD

Add monitoring to your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Start Monitoring
  run: |
    python3 tools/prometheus_exporter.py --port 9090 &
    echo $! > exporter.pid
    
- name: Run Workflow
  run: /dev-orchestrator TICKET-123
  
- name: Collect Metrics
  run: |
    curl -s http://localhost:9090/metrics | grep agent_invocation_total
    kill $(cat exporter.pid)
```

## Related Documentation

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)