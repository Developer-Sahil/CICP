"""
Helper functions for Firebase Firestore operations
Replaces SQLAlchemy-based helpers
"""
from database.firebase_models import Complaint, IssueCluster, Category
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def get_dashboard_stats():
    """
    Get statistics for the admin dashboard.
    
    Returns:
        dict: Dashboard statistics
    """
    try:
        # Total complaints
        all_complaints = Complaint.get_all()
        total_complaints = len(all_complaints)
        
        # Complaints by severity
        severity_stats = {
            'high': sum(1 for c in all_complaints if c.get('severity') == 'high'),
            'medium': sum(1 for c in all_complaints if c.get('severity') == 'medium'),
            'low': sum(1 for c in all_complaints if c.get('severity') == 'low')
        }
        
        # Complaints by category
        category_stats = {}
        categories = Category.get_all()
        for cat in categories:
            count = sum(1 for c in all_complaints if c.get('category') == cat['name'])
            if count > 0:
                category_stats[cat['name']] = count
        
        # Active clusters
        total_clusters = IssueCluster.count()
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_complaints = sum(1 for c in all_complaints 
                               if c.get('timestamp') and 
                               (isinstance(c['timestamp'], datetime) and c['timestamp'] >= week_ago or
                                isinstance(c['timestamp'], str) and datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00')) >= week_ago))
        
        # Top categories
        top_categories = sorted(
            category_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'total_complaints': total_complaints,
            'severity_stats': severity_stats,
            'category_stats': category_stats,
            'total_clusters': total_clusters,
            'recent_complaints': recent_complaints,
            'top_categories': top_categories
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {
            'total_complaints': 0,
            'severity_stats': {'high': 0, 'medium': 0, 'low': 0},
            'category_stats': {},
            'total_clusters': 0,
            'recent_complaints': 0,
            'top_categories': []
        }


def get_recent_complaints(limit=10):
    """
    Get most recent complaints.
    
    Args:
        limit (int): Number of complaints to retrieve
        
    Returns:
        list: List of complaint dicts
    """
    try:
        complaints = Complaint.get_all(limit=limit)
        
        # Convert timestamp strings to datetime objects
        for c in complaints:
            if isinstance(c.get('timestamp'), str):
                try:
                    c['timestamp'] = datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00'))
                except:
                    c['timestamp'] = datetime.utcnow()
        
        return complaints
        
    except Exception as e:
        logger.error(f"Error getting recent complaints: {e}")
        return []


def get_trending_issues(days=7, limit=5):
    """
    Get trending issues based on recent complaint volume.
    
    Args:
        days (int): Number of days to look back
        limit (int): Number of trending issues to return
        
    Returns:
        list: List of (cluster, recent_count) tuples
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all clusters
        clusters = IssueCluster.get_all()
        
        trending = []
        
        for cluster in clusters:
            # Get recent complaints for this cluster
            all_cluster_complaints = Complaint.get_by_cluster(cluster['id'])
            
            recent_count = sum(1 for c in all_cluster_complaints
                             if c.get('timestamp') and
                             (isinstance(c['timestamp'], datetime) and c['timestamp'] >= cutoff_date or
                              isinstance(c['timestamp'], str) and datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00')) >= cutoff_date))
            
            if recent_count > 0:
                trending.append((cluster, recent_count))
        
        # Sort by recent count
        trending.sort(key=lambda x: x[1], reverse=True)
        
        return trending[:limit]
        
    except Exception as e:
        logger.error(f"Error getting trending issues: {e}")
        return []


def format_timestamp(timestamp):
    """
    Format timestamp for display.
    
    Args:
        timestamp (datetime or str): Timestamp to format
        
    Returns:
        str: Formatted timestamp
    """
    if not timestamp:
        return "Unknown"
    
    # Convert string to datetime if needed
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            return "Unknown"
    
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff.days > 7:
        return timestamp.strftime("%b %d, %Y")
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def get_severity_color(severity):
    """
    Get color class for severity level.
    
    Args:
        severity (str): Severity level
        
    Returns:
        str: CSS color class
    """
    colors = {
        'high': 'danger',
        'medium': 'warning',
        'low': 'success'
    }
    return colors.get(severity, 'secondary')


def anonymize_student_id(student_id):
    """
    Anonymize student ID for display.
    
    Args:
        student_id (str): Student ID
        
    Returns:
        str: Anonymized ID
    """
    if not student_id or student_id == 'anonymous':
        return "Anonymous"
    
    # Show only first 3 and last 2 characters
    if len(student_id) > 5:
        return f"{student_id[:3]}***{student_id[-2:]}"
    else:
        return "Anonymous"