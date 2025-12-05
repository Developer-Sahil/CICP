from database.models import db, Complaint, IssueCluster
from ai.embed import cosine_similarity
import config
from datetime import datetime

def assign_cluster(complaint):
    """
    Assign a complaint to an existing cluster or create a new one.
    
    Args:
        complaint (Complaint): The complaint object to cluster
        
    Returns:
        int: Cluster ID
    """
    try:
        # Get all existing clusters with same category and severity
        potential_clusters = IssueCluster.query.filter_by(
            category=complaint.category,
            severity=complaint.severity
        ).all()
        
        if not potential_clusters:
            # Create new cluster
            return create_new_cluster(complaint)
        
        # Get complaint embedding
        target_embedding = complaint.get_embedding()
        if target_embedding is None:
            # If no embedding, just use the first matching cluster
            return potential_clusters[0].id
        
        # Find most similar cluster
        best_cluster = None
        best_similarity = 0.0
        
        for cluster in potential_clusters:
            # Get complaints in this cluster
            cluster_complaints = cluster.complaints.limit(5).all()
            
            if not cluster_complaints:
                continue
            
            # Calculate average similarity to cluster
            similarities = []
            for c in cluster_complaints:
                c_embedding = c.get_embedding()
                if c_embedding is not None:
                    sim = cosine_similarity(target_embedding, c_embedding)
                    similarities.append(sim)
            
            if similarities:
                avg_similarity = sum(similarities) / len(similarities)
                
                if avg_similarity > best_similarity:
                    best_similarity = avg_similarity
                    best_cluster = cluster
        
        # If similarity is above threshold, assign to best cluster
        if best_cluster and best_similarity >= config.SIMILARITY_THRESHOLD:
            return best_cluster.id
        else:
            # Create new cluster
            return create_new_cluster(complaint)
            
    except Exception as e:
        print(f"Error assigning cluster: {e}")
        # Create new cluster as fallback
        return create_new_cluster(complaint)


def create_new_cluster(complaint):
    """
    Create a new cluster for a complaint.
    
    Args:
        complaint (Complaint): The complaint to create cluster for
        
    Returns:
        int: New cluster ID
    """
    cluster_name = f"{complaint.category} - {complaint.severity.upper()}"
    
    cluster = IssueCluster(
        cluster_name=cluster_name,
        category=complaint.category,
        severity=complaint.severity,
        count=1,
        last_updated=datetime.utcnow()
    )
    
    db.session.add(cluster)
    db.session.commit()
    
    return cluster.id


def update_clusters():
    """
    Update all cluster statistics (counts, last_updated).
    """
    try:
        clusters = IssueCluster.query.all()
        
        for cluster in clusters:
            cluster.update_count()
        
        db.session.commit()
        
    except Exception as e:
        print(f"Error updating clusters: {e}")
        db.session.rollback()


def merge_clusters(cluster_id1, cluster_id2):
    """
    Merge two clusters into one.
    
    Args:
        cluster_id1 (int): First cluster ID (will be kept)
        cluster_id2 (int): Second cluster ID (will be merged into first)
        
    Returns:
        bool: Success status
    """
    try:
        cluster1 = IssueCluster.query.get(cluster_id1)
        cluster2 = IssueCluster.query.get(cluster_id2)
        
        if not cluster1 or not cluster2:
            return False
        
        # Move all complaints from cluster2 to cluster1
        complaints = Complaint.query.filter_by(cluster_id=cluster_id2).all()
        for complaint in complaints:
            complaint.cluster_id = cluster_id1
        
        # Delete cluster2
        db.session.delete(cluster2)
        
        # Update cluster1 count
        cluster1.update_count()
        
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Error merging clusters: {e}")
        db.session.rollback()
        return False


def get_cluster_summary(cluster_id, max_complaints=5):
    """
    Get a summary of complaints in a cluster.
    
    Args:
        cluster_id (int): Cluster ID
        max_complaints (int): Maximum number of complaints to include
        
    Returns:
        dict: Cluster summary
    """
    try:
        cluster = IssueCluster.query.get(cluster_id)
        if not cluster:
            return None
        
        complaints = cluster.complaints.order_by(
            Complaint.timestamp.desc()
        ).limit(max_complaints).all()
        
        return {
            'id': cluster.id,
            'name': cluster.cluster_name,
            'category': cluster.category,
            'severity': cluster.severity,
            'count': cluster.count,
            'last_updated': cluster.last_updated,
            'complaints': [
                {
                    'id': c.id,
                    'text': c.rewritten_text,
                    'timestamp': c.timestamp
                }
                for c in complaints
            ]
        }
        
    except Exception as e:
        print(f"Error getting cluster summary: {e}")
        return None