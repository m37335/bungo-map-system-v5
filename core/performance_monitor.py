"""
パフォーマンス監視システム v5.0
作成日: 2025年6月25日
目的: システム全体のパフォーマンス監視とボトルネック特定
"""

import time
import psutil
import logging
import sqlite3
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from functools import wraps
import json
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""
    timestamp: datetime
    operation: str
    duration_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    query_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    error_count: int = 0
    request_size_bytes: int = 0
    response_size_bytes: int = 0

@dataclass
class SystemHealth:
    """システムヘルス情報"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    database_size_mb: float
    cache_hit_rate: float
    active_connections: int
    average_response_time_ms: float
    error_rate_percent: float

class PerformanceMonitor:
    """パフォーマンス監視マネージャー"""
    
    def __init__(
        self,
        db_path: str = "data/performance_metrics.db",
        retention_days: int = 7,
        sample_interval: int = 60,
        alert_thresholds: Dict[str, float] = None
    ):
        self.db_path = Path(db_path)
        self.retention_days = retention_days
        self.sample_interval = sample_interval
        
        # デフォルトアラート閾値
        self.alert_thresholds = alert_thresholds or {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'response_time_ms': 5000.0,
            'error_rate_percent': 5.0,
            'cache_hit_rate': 0.6  # 60%未満でアラート
        }
        
        # メトリクス一時保存
        self.metrics_buffer: List[PerformanceMetrics] = []
        self.buffer_size = 1000
        
        # 監視状態
        self.monitoring_active = False
        self.last_cleanup = datetime.now()
        
        self._initialize_database()
    
    def _initialize_database(self):
        """データベースの初期化"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        duration_ms REAL NOT NULL,
                        memory_usage_mb REAL NOT NULL,
                        cpu_usage_percent REAL NOT NULL,
                        query_count INTEGER DEFAULT 0,
                        cache_hits INTEGER DEFAULT 0,
                        cache_misses INTEGER DEFAULT 0,
                        error_count INTEGER DEFAULT 0,
                        request_size_bytes INTEGER DEFAULT 0,
                        response_size_bytes INTEGER DEFAULT 0
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_health (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        cpu_percent REAL NOT NULL,
                        memory_percent REAL NOT NULL,
                        disk_usage_percent REAL NOT NULL,
                        database_size_mb REAL NOT NULL,
                        cache_hit_rate REAL NOT NULL,
                        active_connections INTEGER NOT NULL,
                        average_response_time_ms REAL NOT NULL,
                        error_rate_percent REAL NOT NULL
                    )
                """)
                
                # インデックスの作成
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp 
                    ON performance_metrics(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_performance_metrics_operation 
                    ON performance_metrics(operation, timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_system_health_timestamp 
                    ON system_health(timestamp)
                """)
                
            logger.info("Performance monitoring database initialized")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    def record_metric(self, metric: PerformanceMetrics):
        """メトリクスの記録"""
        self.metrics_buffer.append(metric)
        
        # バッファが満杯の場合は永続化
        if len(self.metrics_buffer) >= self.buffer_size:
            asyncio.create_task(self._flush_metrics())
    
    async def _flush_metrics(self):
        """メトリクスの永続化"""
        if not self.metrics_buffer:
            return
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for metric in self.metrics_buffer:
                    cursor.execute("""
                        INSERT INTO performance_metrics (
                            timestamp, operation, duration_ms, memory_usage_mb,
                            cpu_usage_percent, query_count, cache_hits, cache_misses,
                            error_count, request_size_bytes, response_size_bytes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        metric.timestamp.isoformat(),
                        metric.operation,
                        metric.duration_ms,
                        metric.memory_usage_mb,
                        metric.cpu_usage_percent,
                        metric.query_count,
                        metric.cache_hits,
                        metric.cache_misses,
                        metric.error_count,
                        metric.request_size_bytes,
                        metric.response_size_bytes
                    ))
                
                conn.commit()
                
            logger.debug(f"Flushed {len(self.metrics_buffer)} metrics to database")
            self.metrics_buffer.clear()
            
        except Exception as e:
            logger.error(f"Failed to flush metrics: {str(e)}")
    
    def get_system_health(self) -> SystemHealth:
        """現在のシステムヘルス情報を取得"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory_info = psutil.virtual_memory()
            memory_percent = memory_info.percent
            
            # ディスク使用率
            disk_info = psutil.disk_usage('/')
            disk_percent = (disk_info.used / disk_info.total) * 100
            
            # データベースサイズ
            db_size_mb = 0
            if self.db_path.exists():
                db_size_mb = self.db_path.stat().st_size / (1024 * 1024)
            
            # 最近のメトリクスから統計を計算
            recent_stats = self._get_recent_statistics()
            
            return SystemHealth(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_percent,
                database_size_mb=db_size_mb,
                cache_hit_rate=recent_stats.get('cache_hit_rate', 0.0),
                active_connections=recent_stats.get('active_connections', 0),
                average_response_time_ms=recent_stats.get('avg_response_time', 0.0),
                error_rate_percent=recent_stats.get('error_rate', 0.0)
            )
            
        except Exception as e:
            logger.error(f"Failed to get system health: {str(e)}")
            return SystemHealth(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                database_size_mb=0.0,
                cache_hit_rate=0.0,
                active_connections=0,
                average_response_time_ms=0.0,
                error_rate_percent=100.0
            )
    
    def _get_recent_statistics(self, hours: int = 1) -> Dict[str, float]:
        """最近の統計情報を取得"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 基本統計
                cursor.execute("""
                    SELECT 
                        AVG(duration_ms) as avg_response_time,
                        SUM(cache_hits) as total_cache_hits,
                        SUM(cache_misses) as total_cache_misses,
                        SUM(error_count) as total_errors,
                        COUNT(*) as total_operations
                    FROM performance_metrics 
                    WHERE timestamp >= ?
                """, (since.isoformat(),))
                
                row = cursor.fetchone()
                
                if row and row[4] > 0:  # total_operations > 0
                    total_cache_ops = (row[1] or 0) + (row[2] or 0)
                    cache_hit_rate = (row[1] or 0) / total_cache_ops if total_cache_ops > 0 else 0.0
                    error_rate = ((row[3] or 0) / row[4]) * 100
                    
                    return {
                        'avg_response_time': row[0] or 0.0,
                        'cache_hit_rate': cache_hit_rate,
                        'error_rate': error_rate,
                        'active_connections': 1  # 簡略化
                    }
                
                return {
                    'avg_response_time': 0.0,
                    'cache_hit_rate': 0.0,
                    'error_rate': 0.0,
                    'active_connections': 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get recent statistics: {str(e)}")
            return {'avg_response_time': 0.0, 'cache_hit_rate': 0.0, 'error_rate': 0.0, 'active_connections': 0}
    
    def check_alerts(self, health: SystemHealth) -> List[Dict[str, Any]]:
        """アラート条件をチェック"""
        alerts = []
        
        # CPU使用率チェック
        if health.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f'CPU usage is {health.cpu_percent:.1f}%',
                'value': health.cpu_percent,
                'threshold': self.alert_thresholds['cpu_percent']
            })
        
        # メモリ使用率チェック
        if health.memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'severity': 'warning',
                'message': f'Memory usage is {health.memory_percent:.1f}%',
                'value': health.memory_percent,
                'threshold': self.alert_thresholds['memory_percent']
            })
        
        return alerts
    
    async def start_monitoring(self):
        """監視の開始"""
        self.monitoring_active = True
        logger.info("Performance monitoring started")
        
        while self.monitoring_active:
            try:
                # システムヘルス情報の取得と保存
                health = self.get_system_health()
                await self._save_system_health(health)
                
                # アラートチェック
                alerts = self.check_alerts(health)
                if alerts:
                    await self._handle_alerts(alerts)
                
                # 定期クリーンアップ
                if datetime.now() - self.last_cleanup > timedelta(hours=24):
                    await self._cleanup_old_data()
                    self.last_cleanup = datetime.now()
                
                # メトリクスバッファのフラッシュ
                if self.metrics_buffer:
                    await self._flush_metrics()
                
                await asyncio.sleep(self.sample_interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {str(e)}")
                await asyncio.sleep(self.sample_interval)
    
    async def stop_monitoring(self):
        """監視の停止"""
        self.monitoring_active = False
        await self._flush_metrics()  # 残りのメトリクスをフラッシュ
        logger.info("Performance monitoring stopped")
    
    async def _save_system_health(self, health: SystemHealth):
        """システムヘルス情報の保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO system_health (
                        timestamp, cpu_percent, memory_percent, disk_usage_percent,
                        database_size_mb, cache_hit_rate, active_connections,
                        average_response_time_ms, error_rate_percent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    health.timestamp.isoformat(),
                    health.cpu_percent,
                    health.memory_percent,
                    health.disk_usage_percent,
                    health.database_size_mb,
                    health.cache_hit_rate,
                    health.active_connections,
                    health.average_response_time_ms,
                    health.error_rate_percent
                ))
                
        except Exception as e:
            logger.error(f"Failed to save system health: {str(e)}")
    
    async def _handle_alerts(self, alerts: List[Dict[str, Any]]):
        """アラートの処理"""
        for alert in alerts:
            if alert['severity'] == 'critical':
                logger.critical(f"CRITICAL ALERT: {alert['message']}")
            elif alert['severity'] == 'warning':
                logger.warning(f"WARNING ALERT: {alert['message']}")
            else:
                logger.info(f"INFO ALERT: {alert['message']}")
    
    async def _cleanup_old_data(self):
        """古いデータのクリーンアップ"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            with sqlite3.connect(self.db_path) as conn:
                # 古いパフォーマンスメトリクスを削除
                cursor = conn.execute("""
                    DELETE FROM performance_metrics 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                deleted_metrics = cursor.rowcount
                
                # 古いシステムヘルス情報を削除
                cursor = conn.execute("""
                    DELETE FROM system_health 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                deleted_health = cursor.rowcount
                
                conn.commit()
                
            logger.info(f"Cleaned up {deleted_metrics} metrics and {deleted_health} health records")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """パフォーマンスレポートの取得"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 操作別統計
                cursor.execute("""
                    SELECT 
                        operation,
                        COUNT(*) as count,
                        AVG(duration_ms) as avg_duration,
                        MIN(duration_ms) as min_duration,
                        MAX(duration_ms) as max_duration
                    FROM performance_metrics 
                    WHERE timestamp >= ?
                    GROUP BY operation
                    ORDER BY avg_duration DESC
                """, (since.isoformat(),))
                
                operation_stats = [
                    {
                        'operation': row[0],
                        'count': row[1],
                        'avg_duration_ms': round(row[2], 2),
                        'min_duration_ms': round(row[3], 2),
                        'max_duration_ms': round(row[4], 2)
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    'report_period_hours': hours,
                    'generated_at': datetime.now().isoformat(),
                    'operation_statistics': operation_stats
                }
                
        except Exception as e:
            logger.error(f"Failed to generate performance report: {str(e)}")
            return {'error': str(e)}


def performance_monitor_decorator(operation_name: str = None):
    """パフォーマンス監視デコレータ"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 監視マネージャーの取得
            monitor = kwargs.get('performance_monitor')
            if not monitor or not isinstance(monitor, PerformanceMonitor):
                return await func(*args, **kwargs)
            
            # 操作名の決定
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            # 開始時の測定
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            
            error_count = 0
            
            try:
                # 関数実行
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                error_count = 1
                logger.error(f"Error in {op_name}: {str(e)}")
                raise
                
            finally:
                # 終了時の測定
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / (1024 * 1024)
                
                duration_ms = (end_time - start_time) * 1000
                avg_memory = (start_memory + end_memory) / 2
                
                # メトリクス記録
                metric = PerformanceMetrics(
                    timestamp=datetime.now(),
                    operation=op_name,
                    duration_ms=duration_ms,
                    memory_usage_mb=avg_memory,
                    cpu_usage_percent=0.0,  # 簡略化
                    error_count=error_count
                )
                
                monitor.record_metric(metric)
        
        return wrapper
    return decorator


# 使用例
async def example_monitoring():
    """パフォーマンス監視の使用例"""
    monitor = PerformanceMonitor()
    
    # システムヘルスチェック
    health = monitor.get_system_health()
    print(f"System Health: CPU={health.cpu_percent:.1f}%, Memory={health.memory_percent:.1f}%")
    
    # アラートチェック
    alerts = monitor.check_alerts(health)
    if alerts:
        print(f"Active alerts: {len(alerts)}")
        for alert in alerts:
            print(f"  - {alert['type']}: {alert['message']}")
    
    # パフォーマンスレポート
    report = monitor.get_performance_report(hours=1)
    print(f"Performance report: {json.dumps(report, indent=2)}")

if __name__ == "__main__":
    asyncio.run(example_monitoring()) 