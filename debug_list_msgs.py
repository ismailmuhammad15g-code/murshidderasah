import asyncio
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from config import Config

async def main():
    client = TelegramClient('anon', Config.TELEGRAM_API_ID, Config.TELEGRAM_API_HASH)
    await client.start()
    ch = await client.get_entity(Config.CHANNEL_USERNAME)
    try:
        await client(JoinChannelRequest(ch))
    except Exception:
        pass
    print(f"Entity: {type(ch)} id={getattr(ch,'id',None)} title={getattr(ch,'title',None)}")
    i = 0
    async for m in client.iter_messages(ch, limit=10):
        i += 1
        t = m.text or ''
        print(f"msg#{i} id={m.id} date={m.date} reply={m.is_reply} len={len(t)} preview={(t[:80]+'...') if len(t)>80 else t}")
    if i==0:
        print('No messages returned by iter_messages.')
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
