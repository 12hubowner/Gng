import os
import staypresent

# Expose a health endpoint so Render knows the bot is alive
staypresent.web.json({"status": "running"})

if __name__ == "__main__":
    # Run bot.py as a subprocess
    # The 'cron' argument pings this URL to prevent Render from sleeping
    staypresent.run(
        "bot.py",
        port=int(os.getenv("PORT", 8080)),
        cron="https://gng-1-z0ht.onrender.com", 
        restart_on_crash=True
    )
