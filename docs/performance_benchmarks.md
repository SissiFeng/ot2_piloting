# Performance Benchmarks

## 1. Test Environment

### 1.1 Hardware Configuration
- CPU: 4 vCPUs (Intel Xeon E5-2686 v4)
- Memory: 16GB RAM
- Storage: SSD (gp3)
- Network: 10 Gbps

### 1.2 Test Scenarios
- Single experiment execution
- Batch processing (10 concurrent experiments)
- Heavy load (100 concurrent users)
- Data consistency verification
- Database query performance

## 2. Latency Metrics

### 2.1 API Response Times (p95)
| Endpoint                  | Latency (ms) | Notes                    |
|--------------------------|--------------|--------------------------|
| User Authentication      | 120          | Including JWT generation |
| Experiment Creation      | 180          | Dual-write operation    |
| Status Query            | 45           | Cached results          |
| Results Retrieval       | 150          | With JSONB parsing      |
| Well Status Update      | 85           | Single operation        |

### 2.2 Database Operations
| Operation               | PostgreSQL (ms) | MongoDB (ms) | Notes                    |
|------------------------|-----------------|--------------|--------------------------|
| Simple Query           | 15             | 12          | Single record retrieval  |
| Complex Join           | 85             | N/A         | Multi-table operation    |
| JSONB Query            | 45             | 35          | Metadata search          |
| Bulk Insert (100 rows) | 250            | 180         | Batch operation         |

### 2.3 Workflow Performance
| Operation                    | Duration (ms) | Notes                         |
|-----------------------------|---------------|-------------------------------|
| Workflow Initialization     | 150          | Including parameter validation|
| OT-2 Command Execution      | 350          | Average per operation        |
| Result Processing           | 200          | Including data transformation|
| Status Update Propagation   | 75           | Real-time updates            |

## 3. Throughput Tests

### 3.1 Concurrent Operations
| Scenario                    | RPS    | Error Rate | Avg Latency (ms) |
|----------------------------|--------|------------|------------------|
| Read Operations            | 1200   | 0.02%      | 85              |
| Write Operations           | 450    | 0.05%      | 220             |
| Mixed Workload             | 800    | 0.03%      | 150             |
| Peak Load (30s)            | 2000   | 0.08%      | 280             |

### 3.2 Database Performance
| Metric                      | Value  | Notes                         |
|----------------------------|--------|-------------------------------|
| Max Connections            | 500    | Configured pool size         |
| Connection Utilization     | 75%    | Under normal load           |
| Cache Hit Ratio            | 95%    | For frequently accessed data|
| Write IOPS                 | 3000   | Sustained rate              |

## 4. Resource Utilization

### 4.1 System Resources
| Component                   | Average | Peak   | Notes                    |
|----------------------------|---------|--------|--------------------------|
| CPU Usage                  | 45%     | 75%    | During batch processing |
| Memory Usage               | 60%     | 85%    | Including cache         |
| Network I/O                | 800Mbps | 2Gbps  | During data sync        |
| Disk I/O                   | 2000 IOPs| 5000 IOPs| Write-heavy workload |

### 4.2 Service Resources
| Service                    | CPU (cores) | Memory (GB) | Notes                    |
|---------------------------|-------------|-------------|--------------------------|
| FastAPI Backend           | 1.5         | 4.0        | Per instance            |
| Prefect Worker            | 1.0         | 3.0        | Per worker              |
| PostgreSQL                | 2.0         | 6.0        | Primary instance        |
| MongoDB                   | 1.5         | 4.0        | Per node                |

## 5. Scalability Tests

### 5.1 Horizontal Scaling
| Instance Count            | Max RPS | Latency (ms) | Notes                    |
|--------------------------|---------|--------------|--------------------------|
| 2 nodes                  | 2400    | 120         | Linear scaling          |
| 4 nodes                  | 4600    | 135         | Near-linear scaling     |
| 8 nodes                  | 8800    | 155         | Some overhead observed  |

### 5.2 Data Volume Impact
| Data Size                | Query Time (ms) | Notes                         |
|-------------------------|-----------------|-------------------------------|
| 1GB                     | 85             | Baseline performance         |
| 10GB                    | 110            | With indexes                 |
| 100GB                   | 180            | Some degradation observed    |

## 6. Optimization Results

### 6.1 Query Optimization
| Optimization              | Improvement | Notes                         |
|--------------------------|-------------|-------------------------------|
| Index Tuning             | 45%         | For common queries           |
| Query Rewriting          | 30%         | Complex joins                |
| Materialized Views       | 65%         | For analytics queries        |
| Connection Pooling       | 25%         | Reduced overhead            |

### 6.2 Caching Impact
| Cache Type               | Hit Rate | Latency Reduction | Notes                    |
|-------------------------|----------|------------------|--------------------------|
| Application Cache       | 92%      | 75%             | In-memory cache         |
| Database Cache          | 88%      | 60%             | Buffer pool             |
| Result Cache            | 95%      | 85%             | For read-heavy ops      | 