import json, urllib.request, urllib.parse, time, re, interactions, datetime, asyncio, random
hglogin = {"email":"<hg_email>","password":"<hg_password>"}
client = interactions.Client("<discord_bot_token>")
discord_channel = <discord_channel_id> # THIS CHANNEL WILL BE CLEARED EVERY TIME BOT STARTS... !!! BEWARE !!!
update_minutes = 5 # How often to query the honeygain API (quicker than 2 mins makes no sense...)
refresh_status = True
automatic_pot = True
warn_offline = True

devcache = None
@client.event
async def on_ready():
    global update_minutes, devcache
    print(f"We're online! We've logged in as {client.me.name}.")
    print(f'Clearing Channel...')
    logs_channel = await interactions.get(client, interactions.Channel, object_id=discord_channel)
    await logs_channel.purge(amount=100)
    devdata, devembeds = get_devices()
    initialmsg = await logs_channel.send(embeds=devembeds)
    prevutcdate = None
    prevlpotmsg = None
    lpotcounter = -1
    while True:
        await asyncio.sleep(int(update_minutes*60))
        devcache = devdata
        utcdate = datetime.datetime.utcnow().strftime("%Y%m%d")
        if utcdate != prevutcdate:
            prevutcdate = utcdate
            print(f'Sleeping 15 minutes for UTC date change...')
            # we must wait 10 minutes before honeygain API becomes responsive again after UTC date change
            await asyncio.sleep(int(15*60))
            lpotcounter = random.randint(1, int(60/update_minutes))
            # print(f"It's a new UTC day, so {int(lpotcounter*update_minutes)} mins until lucky pot try")
        if refresh_status == True:
            old_dev_dict = {}
            for dev in devdata:
                old_dev_dict[dev["id"]] = dev
            devdata, devembeds = get_devices()
            if warn_offline:
                for dev in devdata:
                    if dev["id"] in old_dev_dict:
                        old_dev = old_dev_dict[dev["id"]]
                        if old_dev["status"] != "inactive" and dev["status"] == "inactive":
                            await logs_channel.send(f"@everyone {get_nickname(dev['id'][-4:])} went inactive!")
            await initialmsg.edit(embeds=devembeds)

        if automatic_pot == True:
            # print(f'UTCDATA: {utcdate}')
            if lpotcounter > 0:
                lpotcounter = lpotcounter - 1
            elif lpotcounter == 0:
                try:
                    if prevlpotmsg != None:
                        await prevlpotmsg.delete()
                except Exception as e:
                    pass
                try:
                    prevlpotmsg = await logs_channel.send(f"Lucky pot {retrieve_pot()['data']['credits']} credits redeemed!")
                except Exception as e:
                    prevlpotmsg = await logs_channel.send(f"Lucky pot could not be redeemed..")
                    pass
                lpotcounter = -1

@client.command(
    name="list",
    description="Query Honeygain & List all honeygain devices",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR
)
async def list(ctx: interactions.CommandContext):
    await ctx.send(embeds=get_devices()[1], ephemeral=True)


matcher = re.compile(r"^(\w{4})\s(.*)$")
@client.command(
    name="nickname",
    description="Set a nickname for a given ID",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    options=[
        interactions.Option(
            name="option",
            description="EX: 1234 mynickname",
            type=interactions.OptionType.STRING,
            required=True,
        ),
    ],
)
async def nickname(ctx: interactions.CommandContext, option: str):
    match = matcher.match(option)
    print(f'Match: {match}')
    print(f'{match[1]} {match[2]}')
    # print(match)
    if match[1] in nicknames:
        nicknames[match[1]] = match[2]
        for entry in nicknames.copy():
            if nicknames[entry] == "unknown":
                del nicknames[entry]
        with open("nicknames.json", "w+") as outfile:
            json.dump(nicknames, outfile, indent=4)
        await ctx.send(f"Set nickname for {match[1]} to {match[2]}", ephemeral=True)
@client.command(
    name="openpot",
    description="Open honeygain lucky pot (manually)",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR
)
async def openpot(ctx: interactions.CommandContext):
    try:
        await ctx.send(f"Here you go! ({retrieve_pot()['data']['credits']} credits)", ephemeral=True)
    except Exception as e:
        await ctx.send(f"Lucky pot could not be redeemed..", ephemeral=True)
        pass
try:
    with open("ipdata.json") as infile:
        ipdata = json.load(infile)
except Exception as e:
    ipdata = {}
    pass
def get_ipdata(ipaddr):
    global ipdata
    updatefile = False
    # print(f'Fetching IP data for {ipaddr}')
    if not ipaddr in ipdata:
        print(f'Fetching data from ipapi.co')
        req = urllib.request.Request(f'https://ipapi.co/{ipaddr}/json')
        response = urllib.request.urlopen(req)
        ipdata[ipaddr] = json.loads(response.read().decode())
        updatefile = True
    if updatefile:
        with open("ipdata.json", "w+") as outfile:
            json.dump(ipdata, outfile, indent=4)
    return(ipdata[ipaddr])

try:
    with open("nicknames.json") as infile:
        nicknames = json.load(infile)
except Exception as e:
    nicknames = {}
    pass
def get_nickname(code):
    global nicknames
    if not code in nicknames:
        nicknames[code] = "unknown"
    return(f"{code} {nicknames[code]}")
    
def get_devices(retry_attempt=False):
    global hglogin
    try:
        with open('hg_token.txt', 'r') as file:
            jwt = file.read().strip()
            print(f'Fetching data from honeygain.com')
            req = urllib.request.Request('https://dashboard.honeygain.com/api/v2/devices', headers={'Authorization': f'Bearer {jwt}'})
            response = urllib.request.urlopen(req)
            devs = json.loads(response.read().decode())
            for i, dev in enumerate(devs.copy()["data"]):
                devs["data"][i]["last_active_time_unix"] = int(time.mktime(time.strptime(dev["last_active_time"], "%Y-%m-%d %H:%M:%S")))
                try:
                    for cdev in devcache["data"]:
                        if dev["id"] == cdev["id"] and cdev["status"] != "pending" and dev["status"] != cdev["status"]:
                            print(f"{get_nickname(dev['id'][-4:])} status is pending to {dev['status']} (undecided)")
                            devs["data"][i]["status"] = "pending"
                            # set status to pending if previous status doesn't equal this one, and previous status isn't pending. (filter status between active/inactive to be "pending".)
                except Exception as e:
                    pass
        # start embed generation
        em=interactions.Embed(title="Client List", description="A full list of clients, activity status, IP addresses, etc.", timestamp=datetime.datetime.utcnow())
        embs = ["", "", ""]
        for dev in devs["data"]:
            embs[0] = f"{embs[0]}\n{get_nickname(dev['id'][-4:])}".strip()
            embs[1] = f"{embs[1]}\n{dev['status']}".strip()
            if dev['status'] == "active" and dev['streaming_enabled'] == True:
                embs[1] = f'{embs[1]} + str'
            iporg = re.sub(r'(-LLC)?-?(AS)?\d+$', '', get_ipdata(dev['ip'])['org'])
            embs[2] = f"{embs[2]}\n{dev['ip']}{str('​ ' * int(16-len(dev['ip'])))}{iporg}".strip()

        em.add_field(name="ID & Nickname", value=embs[0], inline=True)
        em.add_field(name="Activity", value=embs[1], inline=True)
        em.add_field(name="ISP Information", value=embs[2], inline=True)
        em.set_footer(text=f"Last Updated")
        # end embed generation
        return((devs["data"], em))
    except Exception:
        if retry_attempt:
            return(False)
        else:
            print(f'Problem with existing session. Making a new one..')
            data = str(json.dumps(hglogin)).encode('utf-8')
            req = urllib.request.Request('https://dashboard.honeygain.com/api/v1/users/tokens', data=data, headers={'Content-Type': 'application/json'})
            response = urllib.request.urlopen(req)
            jwt = json.loads(response.read().decode())["data"]["access_token"]
            with open('hg_token.txt', 'w+') as file:
                file.write(jwt)
            return(get_devices(retry_attempt=True))
        pass
def retrieve_pot():
    with open('hg_token.txt', 'r') as file:
        jwt = file.read().strip()
        req = urllib.request.Request('https://dashboard.honeygain.com/api/v1/contest_winnings', headers={'Authorization': f'Bearer {jwt}'}, method="POST")
        response = urllib.request.urlopen(req)
        return(json.loads(response.read().decode()))

if __name__ == '__main__':
    client.start()
