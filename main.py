import os
import staypresent

# Expose a health endpoint for Render
staypresent.web.json({"status": "running"})

if __name__ == "__main__":
    # Schedule a self-ping every 4 minutes to prevent Render from sleeping
    staypresent.cron(
        "https://gng-1-z0ht.onrender.com",  # Your Render URL
        interval=240
    )

    # Start the web server and launch bot.py as a subprocess
    staypresent.run(
        "bot.py",
        port=int(os.getenv("PORT", 8080)),
        restart_on_crash=True
    )
