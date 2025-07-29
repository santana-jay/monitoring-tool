import re
import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, F
from collections import defaultdict, Counter
from .models import Ticket, Solution, TicketPattern, Category, TicketSolution


class SolutionSuggestionEngine:
    """
    Engine to suggest solutions based on ticket content and historical data
    """
    
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'can', 'cannot', 'cant', 'wont', 'dont', 'doesnt', 'didnt', 'isnt',
            'arent', 'wasnt', 'werent', 'hasnt', 'havent', 'hadnt', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
    
    def extract_keywords(self, text):
        """Extract meaningful keywords from text"""
        # Convert to lowercase and split into words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Remove stop words and return unique keywords
        keywords = [word for word in words if word not in self.stop_words]
        return list(set(keywords))
    
    def suggest_solutions(self, ticket):
        """
        Suggest solutions for a ticket based on various matching strategies
        """
        suggestions = []
        
        # Extract keywords from ticket title and description
        ticket_text = f"{ticket.title} {ticket.description}"
        ticket_keywords = self.extract_keywords(ticket_text)
        
        # Strategy 1: Category-based matching
        if ticket.category:
            category_solutions = Solution.objects.filter(
                category=ticket.category,
                is_active=True
            ).order_by('-times_successful', '-times_suggested')[:5]
            
            for solution in category_solutions:
                suggestions.append({
                    'solution': solution,
                    'confidence_score': 0.7 + (float(solution.success_rate) / 100) * 0.3,
                    'match_reason': f"Same category: {ticket.category.name}",
                    'suggested_by': 'category_match'
                })
        
        # Strategy 2: Keyword matching
        keyword_solutions = self.find_keyword_matches(ticket_keywords)
        for solution, score, matched_keywords in keyword_solutions:
            suggestions.append({
                'solution': solution,
                'confidence_score': score,
                'match_reason': f"Keyword match: {', '.join(matched_keywords)}",
                'suggested_by': 'keyword_match'
            })
        
        # Strategy 3: Pattern-based matching
        pattern_solutions = self.find_pattern_matches(ticket_keywords, ticket.category)
        for solution, score, pattern_type in pattern_solutions:
            suggestions.append({
                'solution': solution,
                'confidence_score': score,
                'match_reason': f"Pattern match: {pattern_type}",
                'suggested_by': 'pattern_match'
            })
        
        # Strategy 4: Historical success for similar issues
        historical_solutions = self.find_historical_matches(ticket_keywords)
        for solution, score, similarity_reason in historical_solutions:
            suggestions.append({
                'solution': solution,
                'confidence_score': score,
                'match_reason': f"Historical success: {similarity_reason}",
                'suggested_by': 'historical_match'
            })
        
        # Remove duplicates and sort by confidence score
        unique_suggestions = {}
        for suggestion in suggestions:
            solution_id = suggestion['solution'].id
            if solution_id not in unique_suggestions or suggestion['confidence_score'] > unique_suggestions[solution_id]['confidence_score']:
                unique_suggestions[solution_id] = suggestion
        
        # Sort by confidence score and return top 10
        sorted_suggestions = sorted(
            unique_suggestions.values(), 
            key=lambda x: x['confidence_score'], 
            reverse=True
        )[:10]
        
        return sorted_suggestions
    
    def find_keyword_matches(self, ticket_keywords):
        """Find solutions that match ticket keywords"""
        matches = []
        
        solutions = Solution.objects.filter(is_active=True)
        
        for solution in solutions:
            solution_keywords = self.extract_keywords(
                f"{solution.title} {solution.description} {solution.keywords}"
            )
            
            # Find common keywords
            common_keywords = set(ticket_keywords) & set(solution_keywords)
            
            if common_keywords:
                # Calculate match score based on keyword overlap
                overlap_ratio = len(common_keywords) / max(len(ticket_keywords), len(solution_keywords))
                success_bonus = float(solution.success_rate) / 100 * 0.3
                confidence_score = min(0.95, overlap_ratio * 0.7 + success_bonus)
                
                matches.append((solution, confidence_score, list(common_keywords)))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)[:5]
    
    def find_pattern_matches(self, ticket_keywords, category):
        """Find solutions based on detected patterns"""
        matches = []
        
        patterns = TicketPattern.objects.filter(
            is_active=True,
            confidence_score__gte=60
        )
        
        for pattern in patterns:
            pattern_keywords = pattern.matching_keywords.split(',') if pattern.matching_keywords else []
            pattern_keywords = [kw.strip().lower() for kw in pattern_keywords]
            
            # Check for keyword matches
            keyword_matches = set(ticket_keywords) & set(pattern_keywords)
            
            # Check for category match
            category_match = pattern.category == category if pattern.category else False
            
            if keyword_matches or category_match:
                confidence = float(pattern.confidence_score) / 100 * 0.8
                if category_match:
                    confidence += 0.2
                
                for solution in pattern.suggested_solutions.all():
                    matches.append((solution, min(0.95, confidence), pattern.pattern_type))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)[:3]
    
    def find_historical_matches(self, ticket_keywords):
        """Find solutions that worked for similar tickets in the past"""
        matches = []
        
        # Find successful solution applications
        successful_applications = TicketSolution.objects.filter(
            was_successful=True
        ).select_related('ticket', 'solution')
        
        for application in successful_applications:
            # Extract keywords from the original ticket
            ticket_text = f"{application.ticket.title} {application.ticket.description}"
            historical_keywords = self.extract_keywords(ticket_text)
            
            # Find common keywords with current ticket
            common_keywords = set(ticket_keywords) & set(historical_keywords)
            
            if len(common_keywords) >= 2:  # At least 2 common keywords
                overlap_ratio = len(common_keywords) / max(len(ticket_keywords), len(historical_keywords))
                confidence_score = min(0.85, overlap_ratio * 0.6 + 0.2)
                
                similarity_reason = f"Similar to ticket #{application.ticket.id}"
                matches.append((application.solution, confidence_score, similarity_reason))
        
        # Remove duplicates and sort
        unique_matches = {}
        for solution, score, reason in matches:
            if solution.id not in unique_matches or score > unique_matches[solution.id][1]:
                unique_matches[solution.id] = (solution, score, reason)
        
        return sorted(unique_matches.values(), key=lambda x: x[1], reverse=True)[:3]


class PatternAnalyzer:
    """
    Analyze tickets to identify patterns and create automated insights
    """
    
    def __init__(self):
        self.min_pattern_confidence = 70
        self.min_occurrences = 3
    
    def analyze_recent_tickets(self, days=30):
        """Analyze tickets from the last N days to find patterns"""
        cutoff_date = timezone.now() - timedelta(days=days)
        tickets = Ticket.objects.filter(created_at__gte=cutoff_date)
        
        results = {
            'patterns_found': 0,
            'tickets_analyzed': tickets.count()
        }
        
        # Analyze different types of patterns
        results['patterns_found'] += self.analyze_keyword_patterns(tickets)
        results['patterns_found'] += self.analyze_category_patterns(tickets)
        results['patterns_found'] += self.analyze_time_patterns(tickets)
        results['patterns_found'] += self.analyze_user_patterns(tickets)
        
        return results
    
    def analyze_keyword_patterns(self, tickets):
        """Identify common keyword patterns in ticket descriptions"""
        keyword_freq = defaultdict(list)
        
        for ticket in tickets:
            keywords = self.extract_keywords(f"{ticket.title} {ticket.description}")
            for keyword in keywords:
                keyword_freq[keyword].append(ticket)
        
        patterns_created = 0
        
        for keyword, ticket_list in keyword_freq.items():
            if len(ticket_list) >= self.min_occurrences:
                # Calculate confidence based on frequency and resolution success
                resolved_tickets = [t for t in ticket_list if t.status == 'RESOLVED']
                confidence = min(95, (len(ticket_list) / tickets.count()) * 100 + 
                               (len(resolved_tickets) / len(ticket_list)) * 30)
                
                if confidence >= self.min_pattern_confidence:
                    # Find common solutions for these tickets
                    common_solutions = self.find_common_solutions(ticket_list)
                    
                    # Create or update pattern
                    pattern, created = TicketPattern.objects.get_or_create(
                        pattern_type='KEYWORD',
                        matching_keywords=keyword,
                        defaults={
                            'pattern_data': {
                                'keyword': keyword,
                                'ticket_count': len(ticket_list),
                                'resolution_rate': len(resolved_tickets) / len(ticket_list)
                            },
                            'confidence_score': confidence,
                            'times_matched': len(ticket_list)
                        }
                    )
                    
                    if created:
                        patterns_created += 1
                        # Add suggested solutions
                        pattern.suggested_solutions.set(common_solutions)
                    else:
                        # Update existing pattern
                        pattern.times_matched = len(ticket_list)
                        pattern.confidence_score = confidence
                        pattern.last_seen = timezone.now()
                        pattern.save()
        
        return patterns_created
    
    def analyze_category_patterns(self, tickets):
        """Analyze patterns within categories"""
        category_patterns = defaultdict(list)
        
        for ticket in tickets.filter(category__isnull=False):
            category_patterns[ticket.category].append(ticket)
        
        patterns_created = 0
        
        for category, ticket_list in category_patterns.items():
            if len(ticket_list) >= self.min_occurrences:
                # Analyze common words in this category
                all_text = ' '.join([f"{t.title} {t.description}" for t in ticket_list])
                keywords = self.extract_keywords(all_text)
                
                # Find most common keywords
                keyword_counts = Counter(keywords)
                top_keywords = [kw for kw, count in keyword_counts.most_common(10) if count >= 2]
                
                if top_keywords:
                    resolved_tickets = [t for t in ticket_list if t.status == 'RESOLVED']
                    confidence = min(95, (len(resolved_tickets) / len(ticket_list)) * 100)
                    
                    if confidence >= self.min_pattern_confidence:
                        pattern, created = TicketPattern.objects.get_or_create(
                            pattern_type='CATEGORY',
                            category=category,
                            defaults={
                                'pattern_data': {
                                    'category_name': category.name,
                                    'common_keywords': top_keywords,
                                    'ticket_count': len(ticket_list)
                                },
                                'matching_keywords': ','.join(top_keywords),
                                'confidence_score': confidence,
                                'times_matched': len(ticket_list)
                            }
                        )
                        
                        if created:
                            patterns_created += 1
                            # Add common solutions
                            common_solutions = self.find_common_solutions(ticket_list)
                            pattern.suggested_solutions.set(common_solutions)
        
        return patterns_created
    
    def analyze_time_patterns(self, tickets):
        """Analyze time-based patterns (day of week, hour of day)"""
        # This could identify patterns like "printer issues on Monday mornings"
        patterns_created = 0
        
        # Group tickets by day of week
        day_patterns = defaultdict(list)
        for ticket in tickets:
            day_of_week = ticket.created_at.strftime('%A')
            day_patterns[day_of_week].append(ticket)
        
        # Find days with significantly more tickets
        avg_daily_tickets = tickets.count() / 7
        
        for day, ticket_list in day_patterns.items():
            if len(ticket_list) > avg_daily_tickets * 1.5:  # 50% above average
                # Analyze common categories on this day
                category_counts = Counter([t.category.name for t in ticket_list if t.category])
                
                for category_name, count in category_counts.most_common(3):
                    if count >= self.min_occurrences:
                        confidence = min(95, (count / len(ticket_list)) * 100)
                        
                        pattern, created = TicketPattern.objects.get_or_create(
                            pattern_type='TIME',
                            matching_keywords=f"{day}_{category_name}",
                            defaults={
                                'pattern_data': {
                                    'day_of_week': day,
                                    'category': category_name,
                                    'occurrence_count': count
                                },
                                'confidence_score': confidence,
                                'times_matched': count
                            }
                        )
                        
                        if created:
                            patterns_created += 1
        
        return patterns_created
    
    def analyze_user_patterns(self, tickets):
        """Analyze patterns related to specific users or user types"""
        patterns_created = 0
        
        # Group tickets by user
        user_patterns = defaultdict(list)
        for ticket in tickets:
            user_patterns[ticket.created_by].append(ticket)
        
        # Find users with many tickets
        avg_user_tickets = tickets.count() / len(user_patterns) if user_patterns else 0
        
        for user, ticket_list in user_patterns.items():
            if len(ticket_list) >= max(self.min_occurrences, avg_user_tickets * 2):
                # Analyze common issues for this user
                all_text = ' '.join([f"{t.title} {t.description}" for t in ticket_list])
                keywords = self.extract_keywords(all_text)
                
                keyword_counts = Counter(keywords)
                top_keywords = [kw for kw, count in keyword_counts.most_common(5) if count >= 2]
                
                if top_keywords:
                    confidence = min(90, (len(ticket_list) / tickets.count()) * 100 + 30)
                    
                    pattern, created = TicketPattern.objects.get_or_create(
                        pattern_type='USER',
                        matching_keywords=f"user_{user.id}_{top_keywords[0]}",
                        defaults={
                            'pattern_data': {
                                'user_id': user.id,
                                'username': user.username,
                                'common_issues': top_keywords,
                                'ticket_count': len(ticket_list)
                            },
                            'confidence_score': confidence,
                            'times_matched': len(ticket_list)
                        }
                    )
                    
                    if created:
                        patterns_created += 1
        
        return patterns_created
    
    def find_common_solutions(self, tickets):
        """Find solutions that were commonly successful for a list of tickets"""
        solution_counts = defaultdict(int)
        
        for ticket in tickets:
            successful_solutions = TicketSolution.objects.filter(
                ticket=ticket,
                was_successful=True
            )
            for ts in successful_solutions:
                solution_counts[ts.solution] += 1
        
        # Return solutions used successfully for at least 2 tickets
        common_solutions = [
            solution for solution, count in solution_counts.items() 
            if count >= 2
        ]
        
        return common_solutions
    
    def extract_keywords(self, text):
        """Extract keywords from text (same as SolutionSuggestionEngine)"""
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [word for word in words if word not in stop_words]
        return list(set(keywords))