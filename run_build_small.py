import asyncio
import scraper, vector_store

async def main():
    docs = await scraper.scrape_channel()
    if not docs:
        print('No docs to build.')
        return
    subset = docs[:30]
    print(f'Building embeddings for {len(subset)} docs...')
    vector_store.build_database(subset)
    print('Done small build.')

if __name__ == '__main__':
    asyncio.run(main())
