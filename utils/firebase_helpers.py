"""
Helper functions for Firebase Firestore operations
FIXED VERSION with better error handling
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
        logger.info("Getting dashboard stats...")
        
        # Total complaints
        all_complaints = Complaint.get_all()
        total_complaints = len(all_complaints)
        
        logger.info(f"Found {total_complaints} total complaints")
        
        # Complaints by severity
        severity_stats = {
            'high': sum(1 for c in all_complaints if c.get('severity') == 'high'),
            'medium': sum(1 for c in all_complaints if c.get('severity') == 'medium'),
            'low': sum(1 for c in all_complaints if c.get('severity') == 'low')
        }
        
        logger.info(f"Severity: high={severity_stats['high']}, medium={severity_stats['medium']}, low={severity_stats['low']}")
        
        # Complaints by category
        category_stats = {}
        categories = Category.get_all()
        for cat in categories:
            count = sum(1 for c in all_complaints if c.get('category') == cat['name'])
            if count > 0:
                category_stats[cat['name']] = count
        
        logger.info(f"Categories: {category_stats}")
        
        # Active clusters
        total_clusters = IssueCluster.count()
        logger.info(f"Total clusters: {total_clusters}")
        
        # Recent activity (last 7 days)
        from datetime import timezone
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_complaints = 0
        
        for c in all_complaints:
            timestamp = c.get('timestamp')
            if timestamp:
                if isinstance(timestamp, datetime):
                    # Make timezone-aware if it isn't already
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    if timestamp >= week_ago:
                        recent_complaints += 1
                elif isinstance(timestamp, str):
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        if dt >= week_ago:
                            recent_complaints += 1
                    except:
                        pass
        
        logger.info(f"Recent complaints (7 days): {recent_complaints}")
        
        # Top categories
        top_categories = sorted(
            category_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        stats = {
            'total_complaints': total_complaints,
            'severity_stats': severity_stats,
            'category_stats': category_stats,
            'total_clusters': total_clusters,
            'recent_complaints': recent_complaints,
            'top_categories': top_categories
        }
        
        logger.info(f"Dashboard stats complete: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
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
        logger.info(f"Getting {limit} recent complaints...")
        
        complaints = Complaint.get_all(limit=limit)
        
        logger.info(f"Retrieved {len(complaints)} complaints")
        
        # Convert timestamp strings to datetime objects
        for c in complaints:
            if isinstance(c.get('timestamp'), str):
                try:
                    c['timestamp'] = datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00'))
                except:
                    c['timestamp'] = datetime.utcnow()
            elif c.get('timestamp') is None:
                c['timestamp'] = datetime.utcnow()
        
        # Sort by timestamp descending
        complaints.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        
        return complaints[:limit]
        
    except Exception as e:
        logger.error(f"Error getting recent complaints: {e}", exc_info=True)
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
        from datetime import timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get all clusters
        clusters = IssueCluster.get_all()
        
        trending = []
        
        for cluster in clusters:
            # Get recent complaints for this cluster
            all_cluster_complaints = Complaint.get_by_cluster(cluster['id'])
            
            recent_count = 0
            for c in all_cluster_complaints:
                timestamp = c.get('timestamp')
                if timestamp:
                    if isinstance(timestamp, datetime):
                        if timestamp.tzinfo is None:
                            from datetime import timezone
                            timestamp = timestamp.replace(tzinfo=timezone.utc)
                        if timestamp >= cutoff_date:
                            recent_count += 1
                    elif isinstance(timestamp, str):
                        try:
                            from datetime import timezone
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            if dt >= cutoff_date:
                                recent_count += 1
                        except:
                            pass
            
            if recent_count > 0:
                trending.append((cluster, recent_count))
        
        # Sort by recent count
        trending.sort(key=lambda x: x[1], reverse=True)
        
        return trending[:limit]
        
    except Exception as e:
        logger.error(f"Error getting trending issues: {e}", exc_info=True)
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
    
    # Make timezone-aware if needed
    from datetime import timezone
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
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