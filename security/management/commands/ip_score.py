import logging

from django.core.management.base import BaseCommand, CommandError

from security.ip_score import decr_ip_score, get_ip_score, incr_ip_score, reset_ip_score

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Manages IP risk scores: view, reset, increment, or decrement."

    def add_arguments(self, parser):
        parser.add_argument("ip_address", type=str, help="The IP address to manage.")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset the score for the given IP address to 0.",
        )
        parser.add_argument(
            "--incr",
            type=int,
            help="Increment the score by a specified delta (default 10).",
            default=0,
        )
        parser.add_argument(
            "--decr",
            type=int,
            help="Decrement the score by a specified delta (default 5).",
            default=0,
        )

    def handle(self, *args, **options):
        ip_address = options["ip_address"]
        reset = options["reset"]
        incr_delta = options["incr"]
        decr_delta = options["decr"]

        if reset:
            reset_ip_score(ip_address)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully reset score for IP: {ip_address}")
            )
        elif incr_delta > 0:
            new_score = incr_ip_score(ip_address, delta=incr_delta)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully incremented score for IP: {ip_address}. New score: {new_score}"
                )
            )
        elif decr_delta > 0:
            new_score = decr_ip_score(ip_address, delta=decr_delta)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully decremented score for IP: {ip_address}. New score: {new_score}"
                )
            )
        else:
            score = get_ip_score(ip_address)
            self.stdout.write(f"Current score for IP {ip_address}: {score}")
