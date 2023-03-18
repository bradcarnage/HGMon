# HGMon
Honeygain outage detection and lucky pot via a discord bot.

1. Install via pip: json, urllib.request, urllib.parse, time, re, interactions, datetime, asyncio, random
2. Create discord bot, and invite to server.
3. Create private channel with discord bot having administrative perms over it.
4. Add cron entry: `@reboot screen -S hgmon -dm bash -c 'while :; do cd /home/user/hgmon/ ; python3 ./hgmon.py ; sleep 1000 ; done'`
5. Set all credentials in python file
6. Reboot & Enjoy?
