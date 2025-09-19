#!/usr/bin/env python3
"""
Ultra Think Optimizer - Advanced Task Management and Performance Optimization

This module provides:
- Automatic task division and parallel execution
- Resource management and optimization  
- Performance measurement and monitoring
- Dynamic workload balancing
"""

import asyncio
import concurrent.futures
import time
import psutil
import threading
from typing import Dict, List, Callable, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
from functools import wraps
from contextlib import contextmanager


@dataclass
class TaskMetrics:
    """Performance metrics for task execution"""
    task_id: str
    start_time: float
    end_time: Optional[float] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    success: bool = False
    error_message: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """Calculate task duration in seconds"""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time


@dataclass
class ResourceLimits:
    """System resource limits and thresholds"""
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_concurrent_tasks: int = 8
    task_timeout: float = 300.0  # 5 minutes


@dataclass
class OptimizerConfig:
    """Configuration for the Ultra Think Optimizer"""
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    enable_monitoring: bool = True
    log_level: str = "INFO"
    metrics_file: Optional[Path] = None
    chunk_size: int = 100
    adaptive_chunking: bool = True


class ResourceMonitor:
    """Real-time system resource monitoring"""
    
    def __init__(self, config: OptimizerConfig):
        self.config = config
        self.monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._metrics: List[Dict[str, float]] = []
        
    def start_monitoring(self):
        """Start resource monitoring in background thread"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
            
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                metrics = {
                    'timestamp': time.time(),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent,
                    'active_threads': threading.active_count()
                }
                self._metrics.append(metrics)
                
                # Keep only last 100 measurements
                if len(self._metrics) > 100:
                    self._metrics = self._metrics[-100:]
                    
            except Exception as e:
                logging.warning(f"Resource monitoring error: {e}")
            
            time.sleep(1)
            
    def get_current_metrics(self) -> Dict[str, float]:
        """Get current system metrics"""
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
        }
        
    def is_resource_available(self) -> bool:
        """Check if system has available resources for new tasks"""
        metrics = self.get_current_metrics()
        limits = self.config.resource_limits
        
        return (
            metrics['cpu_percent'] < limits.max_cpu_percent and
            metrics['memory_percent'] < limits.max_memory_percent
        )


class TaskDivider:
    """Intelligent task division and chunking"""
    
    def __init__(self, config: OptimizerConfig):
        self.config = config
        
    def divide_data_task(self, data: List[Any], task_func: Callable, 
                        min_chunk_size: int = 10) -> List[Tuple[Callable, List[Any]]]:
        """Divide data processing task into optimal chunks"""
        if len(data) <= min_chunk_size:
            return [(task_func, data)]
            
        # Calculate optimal chunk size based on system resources
        chunk_size = self._calculate_optimal_chunk_size(len(data))
        chunks = []
        
        for i in range(0, len(data), chunk_size):
            chunk_data = data[i:i + chunk_size]
            chunks.append((task_func, chunk_data))
            
        return chunks
        
    def divide_file_task(self, file_paths: List[Path], 
                        task_func: Callable) -> List[Tuple[Callable, List[Path]]]:
        """Divide file processing task into manageable groups"""
        if len(file_paths) <= 5:
            return [(task_func, file_paths)]
            
        # Group files by size for balanced processing
        file_sizes = [(path, path.stat().st_size if path.exists() else 0) 
                     for path in file_paths]
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        
        # Create balanced groups
        num_groups = min(len(file_paths) // 3, self.config.resource_limits.max_concurrent_tasks)
        groups = [[] for _ in range(num_groups)]
        
        for i, (path, _) in enumerate(file_sizes):
            groups[i % num_groups].append(path)
            
        return [(task_func, group) for group in groups if group]
        
    def _calculate_optimal_chunk_size(self, data_size: int) -> int:
        """Calculate optimal chunk size based on system resources and data size"""
        base_chunk_size = self.config.chunk_size
        
        if not self.config.adaptive_chunking:
            return base_chunk_size
            
        # Adjust based on available CPU cores
        cpu_cores = psutil.cpu_count(logical=False) or 1
        memory_gb = psutil.virtual_memory().total / (1024 ** 3)
        
        # Scale chunk size based on system capacity
        scale_factor = min(cpu_cores / 4, memory_gb / 8, 4.0)
        optimal_size = int(base_chunk_size * scale_factor)
        
        # Ensure reasonable bounds
        return max(10, min(optimal_size, data_size // 2))


class ParallelExecutor:
    """High-performance parallel task execution"""
    
    def __init__(self, config: OptimizerConfig):
        self.config = config
        self.monitor = ResourceMonitor(config)
        self.divider = TaskDivider(config)
        self._active_tasks: Dict[str, TaskMetrics] = {}
        
    async def execute_tasks(self, tasks: List[Tuple[Callable, Any]], 
                           task_name: str = "batch") -> List[Any]:
        """Execute tasks in parallel with resource monitoring"""
        self.monitor.start_monitoring()
        
        try:
            # Limit concurrent tasks based on resource availability
            max_workers = min(
                self.config.resource_limits.max_concurrent_tasks,
                len(tasks)
            )
            
            results = []
            semaphore = asyncio.Semaphore(max_workers)
            
            async def execute_single_task(task_id: str, func: Callable, args: Any) -> Any:
                async with semaphore:
                    return await self._execute_with_monitoring(task_id, func, args)
            
            # Create tasks
            coroutines = [
                execute_single_task(f"{task_name}_{i}", func, args)
                for i, (func, args) in enumerate(tasks)
            ]
            
            # Execute with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*coroutines, return_exceptions=True),
                    timeout=self.config.resource_limits.task_timeout
                )
            except asyncio.TimeoutError:
                logging.error(f"Task batch '{task_name}' timed out")
                raise
                
            return results
            
        finally:
            self.monitor.stop_monitoring()
            
    async def _execute_with_monitoring(self, task_id: str, func: Callable, args: Any) -> Any:
        """Execute single task with performance monitoring"""
        metrics = TaskMetrics(task_id=task_id, start_time=time.time())
        self._active_tasks[task_id] = metrics
        
        try:
            # Wait for resource availability
            while not self.monitor.is_resource_available():
                await asyncio.sleep(0.1)
                
            # Record initial resource usage
            initial_metrics = self.monitor.get_current_metrics()
            
            # Execute task
            if asyncio.iscoroutinefunction(func):
                result = await func(args)
            else:
                # Run CPU-bound task in thread pool
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(executor, func, args)
            
            # Record completion
            metrics.end_time = time.time()
            metrics.success = True
            
            final_metrics = self.monitor.get_current_metrics()
            metrics.cpu_usage = final_metrics['cpu_percent'] - initial_metrics['cpu_percent']
            metrics.memory_usage = final_metrics['memory_percent'] - initial_metrics['memory_percent']
            
            return result
            
        except Exception as e:
            metrics.end_time = time.time()
            metrics.error_message = str(e)
            logging.error(f"Task {task_id} failed: {e}")
            raise
            
        finally:
            # Clean up active task tracking
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]
                
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        completed_metrics = [
            metrics for metrics in self._active_tasks.values() 
            if metrics.end_time is not None
        ]
        
        if not completed_metrics:
            return {"message": "No completed tasks to report"}
            
        total_duration = sum(m.duration for m in completed_metrics)
        successful_tasks = sum(1 for m in completed_metrics if m.success)
        
        return {
            "total_tasks": len(completed_metrics),
            "successful_tasks": successful_tasks,
            "success_rate": successful_tasks / len(completed_metrics),
            "total_duration": total_duration,
            "average_duration": total_duration / len(completed_metrics),
            "cpu_usage_avg": sum(m.cpu_usage for m in completed_metrics) / len(completed_metrics),
            "memory_usage_avg": sum(m.memory_usage for m in completed_metrics) / len(completed_metrics),
            "resource_metrics": self.monitor.get_current_metrics()
        }


class UltraThinkOptimizer:
    """Main optimizer class combining all optimization strategies"""
    
    def __init__(self, config: Optional[OptimizerConfig] = None):
        self.config = config or OptimizerConfig()
        self.executor = ParallelExecutor(self.config)
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    async def optimize_data_processing(self, data: List[Any], 
                                     process_func: Callable,
                                     task_name: str = "data_processing") -> List[Any]:
        """Optimize large data processing tasks"""
        logging.info(f"Starting optimized data processing: {len(data)} items")
        
        # Divide task into optimal chunks
        task_chunks = self.executor.divider.divide_data_task(data, process_func)
        
        logging.info(f"Divided into {len(task_chunks)} chunks")
        
        # Execute in parallel
        results = await self.executor.execute_tasks(task_chunks, task_name)
        
        # Flatten results
        flattened_results = []
        for result in results:
            if isinstance(result, list):
                flattened_results.extend(result)
            else:
                flattened_results.append(result)
                
        return flattened_results
        
    async def optimize_file_processing(self, file_paths: List[Path],
                                     process_func: Callable,
                                     task_name: str = "file_processing") -> List[Any]:
        """Optimize file processing tasks"""
        logging.info(f"Starting optimized file processing: {len(file_paths)} files")
        
        # Filter existing files
        existing_files = [path for path in file_paths if path.exists()]
        if len(existing_files) != len(file_paths):
            logging.warning(f"Skipped {len(file_paths) - len(existing_files)} non-existent files")
            
        # Divide task into balanced groups
        task_groups = self.executor.divider.divide_file_task(existing_files, process_func)
        
        logging.info(f"Divided into {len(task_groups)} groups")
        
        # Execute in parallel
        results = await self.executor.execute_tasks(task_groups, task_name)
        
        return results
        
    def performance_monitor(self):
        """Context manager for performance monitoring"""
        @contextmanager
        def monitor():
            self.executor.monitor.start_monitoring()
            start_time = time.time()
            try:
                yield
            finally:
                self.executor.monitor.stop_monitoring()
                duration = time.time() - start_time
                logging.info(f"Operation completed in {duration:.2f}s")
                
        return monitor()
        
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report"""
        report = self.executor.get_performance_report()
        report["optimizer_config"] = {
            "max_concurrent_tasks": self.config.resource_limits.max_concurrent_tasks,
            "chunk_size": self.config.chunk_size,
            "adaptive_chunking": self.config.adaptive_chunking,
            "timeout": self.config.resource_limits.task_timeout
        }
        
        if self.config.metrics_file:
            self._save_metrics_to_file(report)
            
        return report
        
    def _save_metrics_to_file(self, report: Dict[str, Any]):
        """Save performance metrics to file"""
        try:
            with open(self.config.metrics_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logging.info(f"Metrics saved to {self.config.metrics_file}")
        except Exception as e:
            logging.error(f"Failed to save metrics: {e}")


def performance_decorator(optimizer: UltraThinkOptimizer):
    """Decorator for automatic performance optimization"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with optimizer.performance_monitor():
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    loop = asyncio.get_event_loop()
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        return await loop.run_in_executor(executor, func, *args, **kwargs)
        return wrapper
    return decorator


# Example usage and utility functions
async def main():
    """Example usage of Ultra Think Optimizer"""
    # Initialize optimizer with custom config
    config = OptimizerConfig(
        resource_limits=ResourceLimits(max_concurrent_tasks=4),
        chunk_size=50,
        adaptive_chunking=True,
        metrics_file=Path("optimization_metrics.json")
    )
    
    optimizer = UltraThinkOptimizer(config)
    
    # Example: Process large dataset
    test_data = list(range(1000))
    
    def process_item(item):
        """Example processing function"""
        time.sleep(0.01)  # Simulate work
        return item * 2
        
    # Optimize data processing
    results = await optimizer.optimize_data_processing(
        test_data, 
        process_item, 
        "example_processing"
    )
    
    # Get performance report
    report = optimizer.get_optimization_report()
    print(f"Processed {len(results)} items")
    print(f"Success rate: {report['success_rate']:.2%}")
    print(f"Total duration: {report['total_duration']:.2f}s")
    

if __name__ == "__main__":
    asyncio.run(main())