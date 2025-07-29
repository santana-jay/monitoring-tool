from django.core.management.base import BaseCommand
from apps.core.utils import PatternAnalyzer


class Command(BaseCommand):
    help = 'Analyze ticket patterns and update the knowledge base'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to analyze (default: 30)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        days = options['days']
        verbose = options['verbose']
        
        self.stdout.write(f'🔍 Analyzing ticket patterns from the last {days} days...')
        
        analyzer = PatternAnalyzer()
        results = analyzer.analyze_recent_tickets(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Analysis complete!\n'
                f'   📊 Tickets analyzed: {results["tickets_analyzed"]}\n'
                f'   🎯 Patterns found: {results["patterns_found"]}'
            )
        )
        
        if verbose:
            self.stdout.write('\n📋 Pattern analysis details:')
            self.stdout.write(f'   - Analyzed {results["tickets_analyzed"]} tickets')
            self.stdout.write(f'   - Created {results["patterns_found"]} new patterns')
            self.stdout.write('   - Check admin interface to review patterns')