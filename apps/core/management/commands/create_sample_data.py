from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.core.models import Category, Ticket, Solution, TicketComment, TicketSolution
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Create sample data for testing the ticket system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tickets',
            type=int,
            default=50,
            help='Number of sample tickets to create (default: 50)',
        )
        parser.add_argument(
            '--solutions',
            type=int,
            default=20,
            help='Number of sample solutions to create (default: 20)',
        )

    def handle(self, *args, **options):
        num_tickets = options['tickets']
        num_solutions = options['solutions']
        
        self.stdout.write('🏗️  Creating sample data for testing...')
        
        # Create sample users if they don't exist
        users = self.create_sample_users()
        
        # Create categories
        categories = self.create_categories()
        
        # Create solutions
        solutions = self.create_solutions(categories, users, num_solutions)
        
        # Create tickets
        tickets = self.create_tickets(categories, users, num_tickets)
        
        # Add some comments and solution applications
        self.add_interactions(tickets, solutions, users)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Sample data created successfully!\n'
                f'   👥 Users: {len(users)}\n'
                f'   📁 Categories: {len(categories)}\n'
                f'   💡 Solutions: {len(solutions)}\n'
                f'   🎫 Tickets: {len(tickets)}'
            )
        )

    def create_sample_users(self):
        """Create sample users for testing"""
        sample_users = [
            {'username': 'tech1', 'first_name': 'John', 'last_name': 'Smith', 'email': 'john@company.com'},
            {'username': 'tech2', 'first_name': 'Sarah', 'last_name': 'Johnson', 'email': 'sarah@company.com'},
            {'username': 'tech3', 'first_name': 'Mike', 'last_name': 'Brown', 'email': 'mike@company.com'},
            {'username': 'user1', 'first_name': 'Alice', 'last_name': 'Davis', 'email': 'alice@company.com'},
            {'username': 'user2', 'first_name': 'Bob', 'last_name': 'Wilson', 'email': 'bob@company.com'},
        ]
        
        users = []
        for user_data in sample_users:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            if created:
                user.set_password('password123')
                user.save()
            users.append(user)
        
        return users

    def create_categories(self):
        """Create sample categories"""
        categories_data = [
            {'name': 'Hardware Issues', 'description': 'Computer, printer, and device problems', 'color': '#e74c3c'},
            {'name': 'Software Issues', 'description': 'Application and system software problems', 'color': '#3498db'},
            {'name': 'Network Problems', 'description': 'Internet and connectivity issues', 'color': '#2ecc71'},
            {'name': 'Email Issues', 'description': 'Email setup and problems', 'color': '#f39c12'},
            {'name': 'Account Access', 'description': 'Login and permission issues', 'color': '#9b59b6'},
            {'name': 'Security', 'description': 'Security-related concerns', 'color': '#e67e22'},
        ]
        
        categories = []
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            categories.append(category)
        
        return categories

    def create_solutions(self, categories, users, num_solutions):
        """Create sample solutions"""
        solutions_data = [
            {
                'title': 'Restart Computer',
                'description': 'Simple restart to fix most common issues',
                'steps': '1. Save all work\n2. Click Start menu\n3. Click Restart\n4. Wait for system to reboot',
                'keywords': 'restart, reboot, slow, freeze, hang',
                'category': 'Hardware Issues'
            },
            {
                'title': 'Clear Browser Cache',
                'description': 'Fix browser loading issues by clearing cache',
                'steps': '1. Open browser settings\n2. Go to Privacy/Security\n3. Clear browsing data\n4. Select cache and cookies\n5. Clear data',
                'keywords': 'browser, slow, loading, website, cache',
                'category': 'Software Issues'
            },
            {
                'title': 'Check Network Cable',
                'description': 'Verify physical network connection',
                'steps': '1. Check if ethernet cable is plugged in\n2. Try different cable\n3. Check cable for damage\n4. Verify connection lights',
                'keywords': 'network, internet, connection, cable, ethernet',
                'category': 'Network Problems'
            },
            {
                'title': 'Reset Email Password',
                'description': 'Reset password for email account',
                'steps': '1. Go to company portal\n2. Click forgot password\n3. Enter email address\n4. Check email for reset link\n5. Create new password',
                'keywords': 'email, password, login, access, forgot',
                'category': 'Email Issues'
            },
            {
                'title': 'Update Software',
                'description': 'Update application to latest version',
                'steps': '1. Open application\n2. Go to Help menu\n3. Check for updates\n4. Download and install updates\n5. Restart application',
                'keywords': 'update, software, version, install, latest',
                'category': 'Software Issues'
            },
        ]
        
        solutions = []
        category_map = {cat.name: cat for cat in categories}
        
        for i, sol_data in enumerate(solutions_data * (num_solutions // len(solutions_data) + 1)):
            if len(solutions) >= num_solutions:
                break
                
            solution = Solution.objects.create(
                title=f"{sol_data['title']} {i+1}" if i >= len(solutions_data) else sol_data['title'],
                description=sol_data['description'],
                steps=sol_data['steps'],
                keywords=sol_data['keywords'],
                category=category_map.get(sol_data['category']),
                created_by=random.choice(users),
                times_suggested=random.randint(5, 50),
                times_successful=random.randint(2, 40)
            )
            solutions.append(solution)
        
        return solutions

    def create_tickets(self, categories, users, num_tickets):
        """Create sample tickets"""
        ticket_templates = [
            {
                'title': 'Computer won\'t start',
                'description': 'My computer is not turning on when I press the power button. No lights or sounds.',
                'category': 'Hardware Issues',
                'priority': 'HIGH'
            },
            {
                'title': 'Email not receiving messages',
                'description': 'I haven\'t received any emails since yesterday morning. My colleagues say they sent me emails.',
                'category': 'Email Issues',
                'priority': 'MEDIUM'
            },
            {
                'title': 'Software keeps crashing',
                'description': 'The accounting software crashes every time I try to open a large file. Error message appears.',
                'category': 'Software Issues',
                'priority': 'HIGH'
            },
            {
                'title': 'Can\'t connect to WiFi',
                'description': 'My laptop can see the company WiFi but can\'t connect. Password seems correct.',
                'category': 'Network Problems',
                'priority': 'MEDIUM'
            },
            {
                'title': 'Forgot my password',
                'description': 'I can\'t remember my login password for the company system. Need to reset it.',
                'category': 'Account Access',
                'priority': 'LOW'
            },
        ]
        
        tickets = []
        category_map = {cat.name: cat for cat in categories}
        statuses = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']
        
        for i in range(num_tickets):
            template = random.choice(ticket_templates)
            
            # Create ticket with some randomization
            created_date = datetime.now() - timedelta(days=random.randint(1, 60))
            
            ticket = Ticket.objects.create(
                title=f"{template['title']} - #{i+1}",
                description=template['description'],
                category=category_map.get(template['category']),
                priority=template['priority'],
                status=random.choice(statuses),
                created_by=random.choice([u for u in users if not u.username.startswith('tech')]),
                assigned_to=random.choice([u for u in users if u.username.startswith('tech')]) if random.random() > 0.3 else None,
                created_at=created_date,
                system_info={
                    'os': random.choice(['Windows 10', 'Windows 11', 'macOS', 'Linux']),
                    'browser': random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
                }
            )
            
            # Set resolved/closed dates for completed tickets
            if ticket.status in ['RESOLVED', 'CLOSED']:
                ticket.resolved_at = created_date + timedelta(hours=random.randint(1, 72))
                if ticket.status == 'CLOSED':
                    ticket.closed_at = ticket.resolved_at + timedelta(hours=random.randint(1, 24))
                ticket.save()
            
            tickets.append(ticket)
        
        return tickets

    def add_interactions(self, tickets, solutions, users):
        """Add comments and solution applications to tickets"""
        for ticket in random.sample(tickets, min(30, len(tickets))):
            # Add some comments
            if random.random() > 0.5:
                TicketComment.objects.create(
                    ticket=ticket,
                    author=random.choice(users),
                    content=random.choice([
                        "I've tried restarting but the issue persists.",
                        "This worked yesterday but not today.",
                        "Similar issue happened last week.",
                        "Could this be related to the recent software update?",
                        "I'll investigate this further and get back to you.",
                        "Please try the suggested solution and let me know.",
                    ])
                )
            
            # Apply some solutions
            if random.random() > 0.4 and solutions:
                solution = random.choice(solutions)
                TicketSolution.objects.create(
                    ticket=ticket,
                    solution=solution,
                    was_successful=random.choice([True, False, None]),
                    notes=random.choice([
                        "User confirmed this fixed the issue.",
                        "Partially worked, needs additional steps.",
                        "Didn't work, trying alternative approach.",
                        "Solution completed successfully.",
                    ]),
                    applied_by=random.choice([u for u in users if u.username.startswith('tech')])
                )