#!/usr/bin/env python
"""
Cross-platform ban cleanup utility for OnlinePharmacy
Supports both Windows and Unix-like systems
"""

import os
import sys
import subprocess
import datetime
import argparse
import logging
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
LOG_FILE = PROJECT_ROOT / "logs" / "ban_cleanup.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BanCleanupManager:
    """Manager for automated ban cleanup operations"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.python_cmd = self._get_python_command()
        
    def _get_python_command(self):
        """Get the appropriate Python command for this environment"""
        # Try to detect if we're in a virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            # We're in a virtual environment
            return sys.executable
        
        # Try common Python commands
        for cmd in ['python', 'python3', 'py']:
            try:
                result = subprocess.run([cmd, '--version'], 
                                     capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return cmd
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        # Fallback to sys.executable
        return sys.executable
    
    def run_django_command(self, command, description="Django command"):
        """Run a Django management command"""
        logger.info(f"Starting: {description}")
        
        try:
            # Change to project directory
            os.chdir(self.project_root)
            
            # Build command
            cmd = [self.python_cmd, 'manage.py'] + command.split()
            
            # Run command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Success: {description} completed")
                if result.stdout.strip():
                    logger.info(f"Output: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"Error: {description} failed with exit code {result.returncode}")
                if result.stderr.strip():
                    logger.error(f"Error output: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout: {description} took too long")
            return False
        except Exception as e:
            logger.error(f"Exception in {description}: {str(e)}")
            return False
    
    def cleanup_quick(self):
        """Quick cleanup - only expired bans (run every 5 minutes)"""
        logger.info("=== Quick Cleanup Started ===")
        
        success = True
        
        # Cleanup user bans
        if not self.run_django_command("unban_expired", "User ban cleanup"):
            success = False
        
        # Cleanup fingerprint bans
        if not self.run_django_command("fingerprint_ban_cleanup --cleanup", "Fingerprint ban cleanup"):
            success = False
        
        logger.info("=== Quick Cleanup Finished ===")
        return success
    
    def cleanup_full(self):
        """Full cleanup with statistics (run every hour)"""
        logger.info("=== Full Cleanup Started ===")
        
        success = True
        
        # Cleanup user bans
        if not self.run_django_command("unban_expired", "User ban cleanup"):
            success = False
        
        # Cleanup fingerprint bans
        if not self.run_django_command("fingerprint_ban_cleanup --cleanup", "Fingerprint ban cleanup"):
            success = False
        
        # Show statistics
        if not self.run_django_command("fingerprint_ban_cleanup --stats", "Ban statistics"):
            success = False
        
        logger.info("=== Full Cleanup Finished ===")
        return success
    
    def reset_daily(self):
        """Reset rate limits and IP blocks (daily)"""
        logger.info("=== Daily Reset Started ===")
        
        success = True
        
        # Clear rate limits
        if not self.run_django_command("fingerprint_ban_cleanup --clear-rate-limits", "Clear rate limits"):
            success = False
        
        # Clear IP blocks
        if not self.run_django_command("fingerprint_ban_cleanup --clear-ip-blocks", "Clear IP blocks"):
            success = False
        
        # Show post-reset statistics
        if not self.run_django_command("fingerprint_ban_cleanup --stats", "Post-reset statistics"):
            success = False
        
        logger.info("=== Daily Reset Finished ===")
        return success
    
    def show_stats(self):
        """Show current ban statistics"""
        logger.info("=== Statistics Report ===")
        return self.run_django_command("fingerprint_ban_cleanup --stats", "Ban statistics")
    
    def emergency_cleanup(self):
        """Emergency cleanup - clear everything (interactive)"""
        logger.info("=== EMERGENCY CLEANUP STARTED ===")
        
        print("⚠️  EMERGENCY CLEANUP MODE ⚠️")
        print("This will clear ALL rate limits and IP blocks!")
        print("Fingerprint bans will NOT be cleared automatically for security.")
        
        confirmation = input("Are you sure? Type 'YES' to continue: ")
        
        if confirmation == 'YES':
            logger.info("Emergency cleanup confirmed by user")
            
            success = True
            
            # Clear rate limits
            if not self.run_django_command("fingerprint_ban_cleanup --clear-rate-limits", "Emergency: Clear rate limits"):
                success = False
            
            # Clear IP blocks
            if not self.run_django_command("fingerprint_ban_cleanup --clear-ip-blocks", "Emergency: Clear IP blocks"):
                success = False
            
            # Show final stats
            self.run_django_command("fingerprint_ban_cleanup --stats", "Post-emergency statistics")
            
            print("Emergency cleanup completed. Check logs for details.")
            logger.info("Emergency cleanup completed successfully")
            return success
        else:
            logger.info("Emergency cleanup cancelled by user")
            print("Emergency cleanup cancelled.")
            return False
    
    def check_fingerprint(self, fingerprint):
        """Check specific fingerprint information"""
        logger.info(f"Checking fingerprint: {fingerprint[:8]}...")
        return self.run_django_command(
            f"fingerprint_ban_cleanup --fingerprint {fingerprint}", 
            f"Fingerprint check: {fingerprint[:8]}..."
        )


def setup_scheduler(args):
    """Setup automated scheduling for different platforms"""
    
    if os.name == 'nt':  # Windows
        print("Setting up Windows Task Scheduler entries...")
        print("Please create the following scheduled tasks in Task Scheduler:")
        print(f"1. Quick cleanup (every 5 minutes): {sys.executable} {__file__} cleanup")
        print(f"2. Full cleanup (hourly): {sys.executable} {__file__} full")
        print(f"3. Daily reset (2 AM daily): {sys.executable} {__file__} reset")
    else:  # Unix-like
        cron_entries = [
            f"# OnlinePharmacy ban cleanup - every 5 minutes",
            f"*/5 * * * * {sys.executable} {__file__} cleanup",
            f"# OnlinePharmacy full cleanup - hourly",
            f"0 * * * * {sys.executable} {__file__} full",
            f"# OnlinePharmacy daily reset - 2 AM daily",
            f"0 2 * * * {sys.executable} {__file__} reset"
        ]
        
        print("Add these entries to your crontab (run 'crontab -e'):")
        for entry in cron_entries:
            print(entry)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="OnlinePharmacy Ban Cleanup Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s cleanup              # Quick cleanup of expired bans
  %(prog)s full                 # Full cleanup with statistics  
  %(prog)s reset                # Daily reset of rate limits and IP blocks
  %(prog)s stats                # Show current statistics
  %(prog)s emergency            # Emergency cleanup (interactive)
  %(prog)s check abc123def      # Check specific fingerprint
  %(prog)s setup-scheduler      # Show scheduler setup instructions
        """
    )
    
    parser.add_argument('action', 
                       choices=['cleanup', 'full', 'reset', 'stats', 'emergency', 'check', 'setup-scheduler'],
                       help='Action to perform')
    
    parser.add_argument('fingerprint', nargs='?',
                       help='Fingerprint to check (for check action)')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = BanCleanupManager()
    
    # Execute requested action
    try:
        if args.action == 'cleanup':
            success = manager.cleanup_quick()
        elif args.action == 'full':
            success = manager.cleanup_full()
        elif args.action == 'reset':
            success = manager.reset_daily()
        elif args.action == 'stats':
            success = manager.show_stats()
        elif args.action == 'emergency':
            success = manager.emergency_cleanup()
        elif args.action == 'check':
            if not args.fingerprint:
                print("Error: fingerprint argument required for check action")
                return 1
            success = manager.check_fingerprint(args.fingerprint)
        elif args.action == 'setup-scheduler':
            setup_scheduler(args)
            return 0
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())