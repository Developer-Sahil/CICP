from database.models import Complaint, IssueCluster, Category
from sqlalchemy import func
from datetime import datetime, timedelta

def get_dashboard_stats():
    """
    Get statistics for the admin dashboard.
    
    Returns:
        dict: Dashboard statistics
    """
    try:
        # Total complaints
        total_complaints = Complaint.query.count()
        
        # Complaints by severity
        severity_stats = {
            'high': Complaint.query.filter_by(severity='high').count(),
            'medium': Complaint.query.filter_by(severity='medium').count(),
            'low': Complaint.query.filter_by(severity='low').count()
        }
        
        # Complaints by category
        category_stats = {}
        categories = Category.query.all()
        for cat in categories:
            count = Complaint.query.filter_by(category=cat.name).count()
            if count > 0:
                category_stats[cat.name] = count
        
        # Active clusters
        total_clusters = IssueCluster.query.count()
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_complaints = Complaint.query.filter(
            Complaint.timestamp >= week_ago
        ).count()
        
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
        print(f"Error getting dashboard stats: {e}")
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
        list: List of Complaint objects
    """
    try:
        complaints = Complaint.query.order_by(
            Complaint.timestamp.desc()
        ).limit(limit).all()
        
        return complaints
        
    except Exception as e:
        print(f"Error getting recent complaints: {e}")
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
        
        # Get clusters with recent activity
        clusters = IssueCluster.query.filter(
            IssueCluster.last_updated >= cutoff_date
        ).all()
        
        trending = []
        
        for cluster in clusters:
            recent_count = cluster.complaints.filter(
                Complaint.timestamp >= cutoff_date
            ).count()
            
            if recent_count > 0:
                trending.append((cluster, recent_count))
        
        # Sort by recent count
        trending.sort(key=lambda x: x[1], reverse=True)
        
        return trending[:limit]
        
    except Exception as e:
        print(f"Error getting trending issues: {e}")
        return []


def format_timestamp(timestamp):
    """
    Format timestamp for display.
    
    Args:
        timestamp (datetime): Timestamp to format
        
    Returns:
        str: Formatted timestamp
    """
    if not timestamp:
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