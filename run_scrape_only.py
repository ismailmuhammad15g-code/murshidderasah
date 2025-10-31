import asyncio
import scraper

async def main():
    docs = await scraper.scrape_channel()
    if docs is None:
        print('scrape_channel => None (Telethon failure)')
    else:
        print(f'scrape_channel => {len(docs)} docs')
        for d in docs[:5]:
            print(f"- {d['date']} {d['link']} len={len(d['text'])}")

if __name__ == '__main__':
    asyncio.run(main())
