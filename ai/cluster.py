from database.firebase_models import Complaint, IssueCluster
from ai.embed import cosine_similarity
import config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def assign_cluster(complaint):
    """
    Assign a complaint to an existing cluster or create a new one.
    
    Args:
        complaint (dict): The complaint dictionary to cluster
        
    Returns:
        str: Cluster ID, or None if clustering fails
    """
    try:
        # Validate complaint
        if not complaint or not complaint.get('category') or not complaint.get('severity'):
            logger.error("Invalid complaint object for clustering")
            return create_new_cluster(complaint)
        
        # Get all existing clusters with same category and severity
        potential_clusters = IssueCluster.get_by_category_severity(
            complaint['category'],
            complaint['severity']
        )
        
        if not potential_clusters:
            # Create new cluster
            return create_new_cluster(complaint)
        
        # Get complaint embedding
        target_embedding = Complaint.get_embedding(complaint)
        if target_embedding is None:
            # If no embedding, use the first matching cluster or create new
            if potential_clusters:
                return potential_clusters[0]['id']
            return create_new_cluster(complaint)
        
        # Find most similar cluster
        best_cluster = None
        best_similarity = 0.0
        
        for cluster in potential_clusters:
            try:
                # Get complaints in this cluster (limit to recent ones for efficiency)
                cluster_complaints = Complaint.get_by_cluster(cluster['id'])
                cluster_complaints = sorted(cluster_complaints, 
                                          key=lambda x: x.get('timestamp', datetime.min), 
                                          reverse=True)[:5]
                
                if not cluster_complaints:
                    continue
                
                # Calculate average similarity to cluster
                similarities = []
                for c in cluster_complaints:
                    try:
                        c_embedding = Complaint.get_embedding(c)
                        if c_embedding is not None:
                            sim = cosine_similarity(target_embedding, c_embedding)
                            if sim is not None and 0 <= sim <= 1:  # Validate similarity
                                similarities.append(sim)
                    except Exception as e:
                        logger.warning(f"Error calculating similarity for complaint {c['id']}: {e}")
                        continue
                
                if similarities:
                    avg_similarity = sum(similarities) / len(similarities)
                    
                    if avg_similarity > best_similarity:
                        best_similarity = avg_similarity
                        best_cluster = cluster
            
            except Exception as e:
                logger.warning(f"Error processing cluster {cluster['id']}: {e}")
                continue
        
        # If similarity is above threshold, assign to best cluster
        if best_cluster and best_similarity >= config.SIMILARITY_THRESHOLD:
            return best_cluster['id']
        else:
            # Create new cluster
            return create_new_cluster(complaint)
            
    except Exception as e:
        logger.error(f"Unexpected error assigning cluster: {e}")
        return create_new_cluster(complaint)


def create_new_cluster(complaint):
    """
    Create a new cluster for a complaint.
    
    Args:
        complaint (dict): The complaint to create cluster for
        
    Returns:
        str: New cluster ID, or None if creation fails
    """
    try:
        if not complaint or not complaint.get('category') or not complaint.get('severity'):
            logger.error("Invalid complaint for cluster creation")
            return None
        
        cluster_name = f"{complaint['category']} - {complaint['severity'].upper()}"
        
        cluster_data = {
            'cluster_name': cluster_name,
            'category': complaint['category'],
            'severity': complaint['severity'],
            'count': 1
        }
        
        cluster = IssueCluster.create(cluster_data)
        
        if cluster:
            logger.info(f"Created new cluster {cluster['id']}: {cluster_name}")
            return cluster['id']
        
        return None
    
    except Exception as e:
        logger.error(f"Unexpected error creating cluster: {e}")
        return None


def update_clusters():
    """
    Update all cluster statistics (counts, last_updated).
    
    Returns:
        tuple: (success: bool, updated_count: int)
    """
    try:
        clusters = IssueCluster.get_all()
        updated_count = 0
        
        for cluster in clusters:
            try:
                old_count = cluster.get('count', 0)
                new_count = IssueCluster.update_count(cluster['id'])
                
                # Remove empty clusters
                if new_count == 0:
                    logger.info(f"Removing empty cluster {cluster['id']}")
                    IssueCluster.delete(cluster['id'])
                elif old_count != new_count:
                    updated_count += 1
            
            except Exception as e:
                logger.warning(f"Error updating cluster {cluster['id']}: {e}")
                continue
        
        logger.info(f"Updated {updated_count} clusters")
        return True, updated_count
    
    except Exception as e:
        logger.error(f"Unexpected error updating clusters: {e}")
        return False, 0


def merge_clusters(cluster_id1, cluster_id2):
    """
    Merge two clusters into one.
    
    Args:
        cluster_id1 (str): First cluster ID (will be kept)
        cluster_id2 (str): Second cluster ID (will be merged into first)
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        cluster1 = IssueCluster.get_by_id(cluster_id1)
        cluster2 = IssueCluster.get_by_id(cluster_id2)
        
        if not cluster1:
            return False, f"Cluster {cluster_id1} not found"
        
        if not cluster2:
            return False, f"Cluster {cluster_id2} not found"
        
        # Validate clusters can be merged (same category and severity)
        if cluster1['category'] != cluster2['category']:
            return False, "Cannot merge clusters with different categories"
        
        if cluster1['severity'] != cluster2['severity']:
            return False, "Cannot merge clusters with different severity levels"
        
        # Move all complaints from cluster2 to cluster1
        complaints = Complaint.get_by_cluster(cluster_id2)
        moved_count = 0
        
        for complaint in complaints:
            if Complaint.update(complaint['id'], {'cluster_id': cluster_id1}):
                moved_count += 1
        
        # Delete cluster2
        IssueCluster.delete(cluster_id2)
        
        # Update cluster1 count
        IssueCluster.update_count(cluster_id1)
        
        logger.info(f"Merged cluster {cluster_id2} into {cluster_id1}, moved {moved_count} complaints")
        return True, None
    
    except Exception as e:
        logger.error(f"Unexpected error merging clusters: {e}")
        return False, f"Error: {str(e)}"


def get_cluster_summary(cluster_id, max_complaints=5):
    """
    Get a summary of complaints in a cluster.
    
    Args:
        cluster_id (str): Cluster ID
        max_complaints (int): Maximum number of complaints to include
        
    Returns:
        dict: Cluster summary or None if error
    """
    try:
        cluster = IssueCluster.get_by_id(cluster_id)
        if not cluster:
            logger.warning(f"Cluster {cluster_id} not found")
            return None
        
        complaints = Complaint.get_by_cluster(cluster_id)
        complaints = sorted(complaints, 
                          key=lambda x: x.get('timestamp', datetime.min), 
                          reverse=True)[:max_complaints]
        
        return {
            'id': cluster['id'],
            'name': cluster['cluster_name'],
            'category': cluster['category'],
            'severity': cluster['severity'],
            'count': cluster.get('count', 0),
            'last_updated': cluster.get('last_updated').isoformat() if cluster.get('last_updated') else None,
            'complaints': [
                {
                    'id': c['id'],
                    'text': c.get('rewritten_text'),
                    'timestamp': c.get('timestamp').isoformat() if c.get('timestamp') else None
                }
                for c in complaints
            ]
        }
    
    except Exception as e:
        logger.error(f"Unexpected error getting cluster summary: {e}")
        return None


def cleanup_empty_clusters():
    """
    Remove clusters with no complaints.
    
    Returns:
        tuple: (success: bool, deleted_count: int)
    """
    try:
        clusters = IssueCluster.get_all()
        deleted_count = 0
        
        for cluster in clusters:
            if cluster.get('count', 0) == 0:
                IssueCluster.delete(cluster['id'])
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} empty clusters")
        return True, deleted_count
    
    except Exception as e:
        logger.error(f"Unexpected error cleaning up clusters: {e}")
        return False, 0


def recalculate_all_clusters():
    """
    Recalculate cluster assignments for all complaints.
    Useful for fixing clustering issues.
    
    Returns:
        tuple: (success: bool, reassigned_count: int)
    """
    try:
        complaints = Complaint.get_all()
        reassigned_count = 0
        
        for complaint in complaints:
            try:
                old_cluster = complaint.get('cluster_id')
                new_cluster = assign_cluster(complaint)
                
                if new_cluster and new_cluster != old_cluster:
                    Complaint.update(complaint['id'], {'cluster_id': new_cluster})
                    reassigned_count += 1
            
            except Exception as e:
                logger.warning(f"Error reassigning complaint {complaint['id']}: {e}")
                continue
        
        # Update all cluster counts
        update_clusters()
        
        # Clean up empty clusters
        cleanup_empty_clusters()
        
        logger.info(f"Recalculated clusters, reassigned {reassigned_count} complaints")
        return True, reassigned_count
    
    except Exception as e:
        logger.error(f"Unexpected error recalculating clusters: {e}")
        return False, 0