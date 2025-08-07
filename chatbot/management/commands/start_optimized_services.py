"""
Management command to start optimized services
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from chatbot.ml_service import get_ml_service
from chatbot.tasks import preload_models_async
from chatbot.utils import safe_debug_print
import time


class Command(BaseCommand):
    help = 'Start optimized services (ML model preloading, cache warming, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--preload-models',
            action='store_true',
            help='Preload ML models',
        )
        parser.add_argument(
            '--warm-cache',
            action='store_true',
            help='Warm up cache with common queries',
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Run health checks',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting optimized services...'))
        
        # Initialize ML service
        try:
            ml_service = get_ml_service()
            self.stdout.write(self.style.SUCCESS('ML service initialized'))
            
            # Get pool status
            status = ml_service.get_pool_status()
            self.stdout.write(f"Pool status: {status}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to initialize ML service: {e}'))
            return
        
        # Preload models if requested
        if options['preload_models']:
            self.stdout.write('Preloading ML models...')
            try:
                # Preload the main model
                model = ml_service.model_pool.get_model()
                if model:
                    self.stdout.write(self.style.SUCCESS('ML model preloaded successfully'))
                else:
                    self.stdout.write(self.style.ERROR('Failed to preload ML model'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error preloading models: {e}'))
        
        # Warm cache if requested
        if options['warm_cache']:
            self.stdout.write('Warming cache with common queries...')
            try:
                # Common test queries for cache warming
                test_queries = [
                    "My package was delayed",
                    "The customer service was rude",
                    "I want to return this item",
                    "The product is defective",
                    "I received the wrong item"
                ]
                
                for query in test_queries:
                    result, was_cached = ml_service.classify_text(query, use_cache=True)
                    if result:
                        self.stdout.write(f"Cached query: {query[:30]}...")
                    else:
                        self.stdout.write(f"Failed to cache query: {query[:30]}...")
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error warming cache: {e}'))
        
        # Health check if requested
        if options['health_check']:
            self.stdout.write('Running health checks...')
            try:
                from chatbot.utils import get_performance_metrics
                metrics = get_performance_metrics()
                
                memory_usage = metrics.get('memory', {}).get('percent', 0)
                cpu_usage = metrics.get('cpu_percent', 0)
                
                self.stdout.write(f"Memory usage: {memory_usage:.1f}%")
                self.stdout.write(f"CPU usage: {cpu_usage:.1f}%")
                
                if memory_usage < 85 and cpu_usage < 90:
                    self.stdout.write(self.style.SUCCESS('System is healthy'))
                else:
                    self.stdout.write(self.style.WARNING('System resources are high'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error running health checks: {e}'))
        
        self.stdout.write(self.style.SUCCESS('Optimized services started successfully!'))
        self.stdout.write('Services are ready to handle requests with:')
        self.stdout.write('- ML model pooling')
        self.stdout.write('- Redis caching')
        self.stdout.write('- Request queuing')
        self.stdout.write('- Performance monitoring') 