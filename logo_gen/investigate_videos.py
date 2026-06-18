"""Investigate why videos disappeared from parent dashboard."""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = c[os.environ["DB_NAME"]]

    print("=== freebuild_media_assets ===")
    total = await d.freebuild_media_assets.count_documents({})
    print(f"Total docs: {total}")
    approved = await d.freebuild_media_assets.count_documents({"approved": True})
    pending = await d.freebuild_media_assets.count_documents({"approved": False})
    none_app = await d.freebuild_media_assets.count_documents({"approved": {"$exists": False}})
    print(f"  approved=True : {approved}")
    print(f"  approved=False: {pending}")
    print(f"  no-approved-field: {none_app}")

    print("\n=== Latest 8 docs ===")
    async for doc in d.freebuild_media_assets.find().sort("_id", -1).limit(8):
        url = str(doc.get("file_url", ""))[:70]
        approved_v = doc.get("approved")
        type_v = doc.get("type")
        created = doc.get("created_at")
        deleted = doc.get("deleted") or doc.get("is_deleted") or doc.get("removed")
        owner = doc.get("owner") or doc.get("parent_email") or doc.get("created_by")
        print(f"  approved={approved_v} | deleted={deleted} | type={type_v} | owner={owner} | created={created}")
        print(f"    file_url={url}")

    # All collections with media-like names
    cols = await d.list_collection_names()
    media_cols = [c for c in cols if any(k in c.lower() for k in ["media", "video", "kids", "freebuild"])]
    print("\n=== All media-like collections ===")
    for col in sorted(media_cols):
        cnt = await d[col].count_documents({})
        print(f"  {col}: {cnt}")

    # Check users to confirm parent + kids exist
    print("\n=== Users (parents + kids) ===")
    async for u in d.users.find().limit(20):
        print(
            f"  email={u.get('email')} | role={u.get('role')} | name={u.get('name')} | is_owner={u.get('is_owner')}"
        )

    # Check files on disk
    print("\n=== Disk video files ===")
    import os as _os
    paths = ["/opt/zenrex/data/videos", "/opt/zenrex/data/freebuild", "/var/www/pwa_kids/videos", "/opt/zerax/data"]
    for p in paths:
        if _os.path.exists(p):
            try:
                files = _os.listdir(p)
                print(f"  {p}: {len(files)} entries")
                for f in files[:5]:
                    print(f"    - {f}")
            except Exception as e:
                print(f"  {p}: error {e}")
        else:
            print(f"  {p}: NOT EXIST")

    c.close()


if __name__ == "__main__":
    asyncio.run(main())
