#!/usr/bin/env bash
# Idempotent seed: owner@zerax.com / owner123 (role=owner)
# Usage:  docker exec zerax-backend-1 python /app/scripts/seed_owner.py
import asyncio, os, uuid, bcrypt
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    url = os.environ.get('MONGO_URL', 'mongodb://mongo:27017')
    dbn = os.environ.get('DB_NAME', 'zerax_prod')
    db = AsyncIOMotorClient(url)[dbn]

    email = 'owner@zerax.com'
    existing = await db.users.find_one({'email': email})
    if existing:
        await db.users.update_one(
            {'email': email},
            {'$set': {'is_owner': True, 'role': 'owner'}}
        )
        print(f'[seed] updated existing owner -> id={existing.get("id")}')
        return

    uid = str(uuid.uuid4())
    doc = {
        'id': uid,
        'email': email,
        'name': 'Zerax Owner',
        'role': 'owner',
        'is_owner': True,
        'country': 'SA',
        'gender': 'male',
        'credits': 999999,
        'bonus_points': 0,
        'free_images': 9999,
        'free_videos': 9999,
        'free_website_trial': True,
        'password': bcrypt.hashpw(b'owner123', bcrypt.gensalt()).decode(),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'signup_bonus_claimed': True,
    }
    await db.users.insert_one(doc)
    print(f'[seed] created owner -> id={uid}')

if __name__ == '__main__':
    asyncio.run(main())
