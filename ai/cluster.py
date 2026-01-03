from ai.embed import cosine_similarity
import config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def assign_cluster(complaint):
    """
    Assign a complaint to an existing cluster or create a new one.
    
    Args:
        complaint (Complaint): The complaint object to cluster
        
    Returns:
        int: Cluster ID, or None if clustering fails
    """
    try:
        # Validate complaint
        if not complaint or not complaint.category or not complaint.severity:
            logger.error("Invalid complaint object for clustering")
            return create_new_cluster(complaint)
        
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
            # If no embedding, use the first matching cluster or create new
            if potential_clusters:
                return potential_clusters[0].id
            return create_new_cluster(complaint)
        
        # Find most similar cluster
        best_cluster = None
        best_similarity = 0.0
        
        for cluster in potential_clusters:
            try:
                # Get complaints in this cluster (limit to recent ones for efficiency)
                cluster_complaints = cluster.complaints.order_by(
                    Complaint.timestamp.desc()
                ).limit(5).all()
                
                if not cluster_complaints:
                    continue
                
                # Calculate average similarity to cluster
                similarities = []
                for c in cluster_complaints:
                    try:
                        c_embedding = c.get_embedding()
                        if c_embedding is not None:
                            sim = cosine_similarity(target_embedding, c_embedding)
                            if sim is not None and 0 <= sim <= 1:  # Validate similarity
                                similarities.append(sim)
                    except Exception as e:
                        logger.warning(f"Error calculating similarity for complaint {c.id}: {e}")
                        continue
                
                if similarities:
                    avg_similarity = sum(similarities) / len(similarities)
                    
                    if avg_similarity > best_similarity:
                        best_similarity = avg_similarity
                        best_cluster = cluster
            
            except Exception as e:
                logger.warning(f"Error processing cluster {cluster.id}: {e}")
                continue
        
        # If similarity is above threshold, assign to best cluster
        if best_cluster and best_similarity >= config.SIMILARITY_THRESHOLD:
            return best_cluster.id
        else:
            # Create new cluster
            return create_new_cluster(complaint)
            
    except SQLAlchemyError as e:
        logger.error(f"Database error assigning cluster: {e}")
        db.session.rollback()
        return create_new_cluster(complaint)
    
    except Exception as e:
        logger.error(f"Unexpected error assigning cluster: {e}")
        return create_new_cluster(complaint)


def create_new_cluster(complaint):
    """
    Create a new cluster for a complaint.
    
    Args:
        complaint (Complaint): The complaint to create cluster for
        
    Returns:
        int: New cluster ID, or None if creation fails
    """
    try:
        if not complaint or not complaint.category or not complaint.severity:
            logger.error("Invalid complaint for cluster creation")
            return None
        
        cluster_name = f"{complaint.category} - {complaint.severity.upper()}"
        
        cluster = IssueCluster(
            cluster_name=cluster_name,
            category=complaint.category,
            severity=complaint.severity,
            count=1,
            last_updated=datetime.utcnow()
        )
        
        db.session.add(cluster)
        db.session.flush()  # Get ID without committing
        
        logger.info(f"Created new cluster {cluster.id}: {cluster_name}")
        return cluster.id
    
    except SQLAlchemyError as e:
        logger.error(f"Database error creating cluster: {e}")
        db.session.rollback()
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
        clusters = IssueCluster.query.all()
        updated_count = 0
        
        for cluster in clusters:
            try:
                old_count = cluster.count
                cluster.update_count()
                
                # Remove empty clusters
                if cluster.count == 0:
                    logger.info(f"Removing empty cluster {cluster.id}")
                    db.session.delete(cluster)
                elif old_count != cluster.count:
                    updated_count += 1
            
            except Exception as e:
                logger.warning(f"Error updating cluster {cluster.id}: {e}")
                continue
        
        db.session.commit()
        logger.info(f"Updated {updated_count} clusters")
        return True, updated_count
    
    except SQLAlchemyError as e:
        logger.error(f"Database error updating clusters: {e}")
        db.session.rollback()
        return False, 0
    
    except Exception as e:
        logger.error(f"Unexpected error updating clusters: {e}")
        return False, 0


def merge_clusters(cluster_id1, cluster_id2):
    """
    Merge two clusters into one.
    
    Args:
        cluster_id1 (int): First cluster ID (will be kept)
        cluster_id2 (int): Second cluster ID (will be merged into first)
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        cluster1 = IssueCluster.query.get(cluster_id1)
        cluster2 = IssueCluster.query.get(cluster_id2)
        
        if not cluster1:
            return False, f"Cluster {cluster_id1} not found"
        
        if not cluster2:
            return False, f"Cluster {cluster_id2} not found"
        
        # Validate clusters can be merged (same category and severity)
        if cluster1.category != cluster2.category:
            return False, "Cannot merge clusters with different categories"
        
        if cluster1.severity != cluster2.severity:
            return False, "Cannot merge clusters with different severity levels"
        
        # Move all complaints from cluster2 to cluster1
        complaints = Complaint.query.filter_by(cluster_id=cluster_id2).all()
        moved_count = 0
        
        for complaint in complaints:
            complaint.cluster_id = cluster_id1
            moved_count += 1
        
        # Delete cluster2
        db.session.delete(cluster2)
        
        # Update cluster1 count
        cluster1.update_count()
        
        db.session.commit()
        logger.info(f"Merged cluster {cluster_id2} into {cluster_id1}, moved {moved_count} complaints")
        return True, None
    
    except SQLAlchemyError as e:
        logger.error(f"Database error merging clusters: {e}")
        db.session.rollback()
        return False, f"Database error: {str(e)}"
    
    except Exception as e:
        logger.error(f"Unexpected error merging clusters: {e}")
        db.session.rollback()
        return False, f"Error: {str(e)}"


def get_cluster_summary(cluster_id, max_complaints=5):
    """
    Get a summary of complaints in a cluster.
    
    Args:
        cluster_id (int): Cluster ID
        max_complaints (int): Maximum number of complaints to include
        
    Returns:
        dict: Cluster summary or None if error
    """
    try:
        cluster = IssueCluster.query.get(cluster_id)
        if not cluster:
            logger.warning(f"Cluster {cluster_id} not found")
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
            'last_updated': cluster.last_updated.isoformat() if cluster.last_updated else None,
            'complaints': [
                {
                    'id': c.id,
                    'text': c.rewritten_text,
                    'timestamp': c.timestamp.isoformat() if c.timestamp else None
                }
                for c in complaints
            ]
        }
    
    except SQLAlchemyError as e:
        logger.error(f"Database error getting cluster summary: {e}")
        return None
    
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
        empty_clusters = IssueCluster.query.filter_by(count=0).all()
        deleted_count = len(empty_clusters)
        
        for cluster in empty_clusters:
            db.session.delete(cluster)
        
        db.session.commit()
        logger.info(f"Cleaned up {deleted_count} empty clusters")
        return True, deleted_count
    
    except SQLAlchemyError as e:
        logger.error(f"Database error cleaning up clusters: {e}")
        db.session.rollback()
        return False, 0
    
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
        complaints = Complaint.query.all()
        reassigned_count = 0
        
        for complaint in complaints:
            try:
                old_cluster = complaint.cluster_id
                new_cluster = assign_cluster(complaint)
                
                if new_cluster and new_cluster != old_cluster:
                    complaint.cluster_id = new_cluster
                    reassigned_count += 1
            
            except Exception as e:
                logger.warning(f"Error reassigning complaint {complaint.id}: {e}")
                continue
        
        db.session.commit()
        
        # Update all cluster counts
        update_clusters()
        
        # Clean up empty clusters
        cleanup_empty_clusters()
        
        logger.info(f"Recalculated clusters, reassigned {reassigned_count} complaints")
        return True, reassigned_count
    
    except SQLAlchemyError as e:
        logger.error(f"Database error recalculating clusters: {e}")
        db.session.rollback()
        return False, 0
    
    except Exception as e:
        logger.error(f"Unexpected error recalculating clusters: {e}")
        return False, 0