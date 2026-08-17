#!/bin/bash

# Automated ban cleanup script for production
# Add this to crontab for regular cleanup:
#   # Every 5 minutes - cleanup expired bans
#   */5 * * * * /path/to/project/scripts/cleanup_bans.sh cleanup
#   # Every hour - full cleanup with stats
#   0 * * * * /path/to/project/scripts/cleanup_bans.sh full
#   # Every day at 02:00 - clear rate limits and IP blocks
#   0 2 * * * /path/to/project/scripts/cleanup_bans.sh reset

# Configuration
PROJECT_DIR="/path/to/your/project"
PYTHON_PATH="/path/to/your/venv/bin/python"
LOG_FILE="/var/log/pharmacy_cleanup.log"

# Ensure we're in the right directory
cd $PROJECT_DIR

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> $LOG_FILE
}

# Function to run Django command with logging
run_command() {
    local cmd="$1"
    local description="$2"
    
    log_message "Starting: $description"
    
    if $PYTHON_PATH manage.py $cmd >> $LOG_FILE 2>&1; then
        log_message "Success: $description completed"
        return 0
    else
        log_message "Error: $description failed"
        return 1
    fi
}

# Main execution based on argument
case "$1" in
    "cleanup")
        # Quick cleanup - only expired bans
        log_message "=== Quick Cleanup Started ==="
        run_command "unban_expired" "User ban cleanup"
        run_command "fingerprint_ban_cleanup --cleanup" "Fingerprint ban cleanup"
        log_message "=== Quick Cleanup Finished ==="
        ;;
        
    "full")
        # Full cleanup with statistics
        log_message "=== Full Cleanup Started ==="
        run_command "unban_expired" "User ban cleanup"
        run_command "fingerprint_ban_cleanup --cleanup" "Fingerprint ban cleanup"
        run_command "fingerprint_ban_cleanup --stats" "Ban statistics"
        log_message "=== Full Cleanup Finished ==="
        ;;
        
    "reset")
        # Reset rate limits and IP blocks (daily)
        log_message "=== Daily Reset Started ==="
        run_command "fingerprint_ban_cleanup --clear-rate-limits" "Clear rate limits"
        run_command "fingerprint_ban_cleanup --clear-ip-blocks" "Clear IP blocks"
        run_command "fingerprint_ban_cleanup --stats" "Post-reset statistics"
        log_message "=== Daily Reset Finished ==="
        ;;
        
    "stats")
        # Just show statistics
        log_message "=== Statistics Report ==="
        run_command "fingerprint_ban_cleanup --stats" "Ban statistics"
        ;;
        
    "emergency")
        # Emergency cleanup - clear everything
        log_message "=== EMERGENCY CLEANUP STARTED ==="
        
        echo "⚠️  EMERGENCY CLEANUP MODE ⚠️"
        echo "This will clear ALL fingerprint bans, rate limits, and IP blocks!"
        echo "Are you sure? Type 'YES' to continue:"
        read confirmation
        
        if [ "$confirmation" = "YES" ]; then
            log_message "Emergency cleanup confirmed by user"
            
            # Clear all cache-based restrictions
            run_command "fingerprint_ban_cleanup --clear-rate-limits" "Emergency: Clear rate limits"
            run_command "fingerprint_ban_cleanup --clear-ip-blocks" "Emergency: Clear IP blocks"
            
            # Note: We don't auto-clear fingerprint bans in emergency mode
            # as they might be legitimate security measures
            echo "Emergency cleanup completed. Check logs for details."
            log_message "Emergency cleanup completed successfully"
        else
            log_message "Emergency cleanup cancelled by user"
            echo "Emergency cleanup cancelled."
        fi
        ;;
        
    *)
        echo "Usage: $0 {cleanup|full|reset|stats|emergency}"
        echo ""
        echo "Commands:"
        echo "  cleanup   - Quick cleanup of expired bans (run every 5 minutes)"
        echo "  full      - Full cleanup with statistics (run every hour)"
        echo "  reset     - Clear rate limits and IP blocks (run daily)"
        echo "  stats     - Show current ban statistics"
        echo "  emergency - Emergency cleanup of all restrictions (interactive)"
        echo ""
        echo "Example crontab entries:"
        echo "  */5 * * * * $0 cleanup"
        echo "  0 * * * * $0 full"
        echo "  0 2 * * * $0 reset"
        exit 1
        ;;
esac

exit 0