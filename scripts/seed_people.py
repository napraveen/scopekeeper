"""
ScopeKeeper People & Authority Seeding Script.
Aligns Switch Core PostgreSQL with canonical personas:
- Harish: Junior Frontend Dev (Client, Discord, Requester)
- Dhana: Head of Product (Client, Telegram, Authorized Signer, Cap $5,000)
- Sakthi: Lead Project Manager (Agency, Switch Console, Day Leaseholder)
- Bala: Delivery Lead & Reviewer (Agency, Slack, Estimations & PR Reviews)
"""

import asyncio
import asyncpg
import json
import os
import uuid
from datetime import datetime, timezone

DB_URL = os.environ.get("SWITCH_DB_URL") or "postgresql://postgres:oIYBdLrq3PE6xq_mkrgnLTqmrdsKuRtM@127.0.0.1:50417/switch"

async def seed():
    print(f"Connecting to Switch PostgreSQL at {DB_URL}...")
    conn = await asyncpg.connect(DB_URL)
    try:
        now = datetime.now(timezone.utc)
        
        # 1. Update/Verify Agency Users (Sakthi & Bala)
        print("\n--- 1. Seeding Agency Team Members (users & tenant_members) ---")
        admin_user = await conn.fetchrow("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        if admin_user:
            admin_id = admin_user["id"]
            await conn.execute("""
                UPDATE users 
                SET name = 'Sakthi (Lead PM)', email = 'sakthi@scopekeeper.agency', metadata = $1
                WHERE id = $2
            """, json.dumps({"title": "Lead Project Manager", "handle": "sakthi", "roles": ["account-manager", "client-desk"]}), admin_id)
            print(f"  [OK] Updated Admin user to Sakthi (Lead PM) [ID: {admin_id}]")
        
        # Ensure Bala exists in users
        bala_user = await conn.fetchrow("SELECT id FROM users WHERE email = 'bala@scopekeeper.agency'")
        if not bala_user:
            bala_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO users (id, name, email, role, metadata, created_at, workspaces_created)
                VALUES ($1, 'Bala (Delivery Lead)', 'bala@scopekeeper.agency', 'user', $2, $3, 0)
            """, bala_id, json.dumps({"title": "Delivery Lead & Reviewer", "handle": "bala", "roles": ["delivery-lead", "reviewer", "on-call"]}), now)
            # Add to tenant_members
            await conn.execute("""
                INSERT INTO tenant_members (tenant_id, user_id, role, created_at)
                VALUES ('00000000-0000-0000-0000-000000000000', $1, 'member', $2)
                ON CONFLICT (tenant_id, user_id) DO NOTHING
            """, bala_id, now)
            print(f"  [OK] Created Bala (Delivery Lead) in users [ID: {bala_id}]")
        else:
            print("  [OK] Bala already exists in users.")

        # 2. Inspect and Tag External Users across Bridges
        print("\n--- 2. Tagging External Users across Bridges (Harish, Dhana, Bala) ---")
        bridges = await conn.fetch("SELECT id, type, display_name FROM collaboration_bridges")
        bridge_map = {b["id"]: b for b in bridges}
        
        ext_users = await conn.fetch("SELECT id, bridge_id, external_user_id, external_username FROM external_users")
        for eu in ext_users:
            bid = eu["bridge_id"]
            b_info = bridge_map.get(bid)
            b_type = (b_info["type"] if b_info else "").lower()
            
            if "discord" in b_type:
                # Map to Harish (Client Requester)
                await conn.execute("""
                    UPDATE external_users
                    SET external_username = 'Harish (Acme Dev)'
                    WHERE id = $1
                """, eu["id"])
                print(f"  [OK] Mapped Discord user {eu['external_user_id']} -> Harish (Acme Dev) [Requester only]")
                
            elif "telegram" in b_type:
                # Map to Dhana (Client Signer)
                await conn.execute("""
                    UPDATE external_users
                    SET external_username = 'Dhana (Head of Product)'
                    WHERE id = $1
                """, eu["id"])
                print(f"  [OK] Mapped Telegram user {eu['external_user_id']} -> Dhana (Head of Product) [Authorized Signer, Cap: $5,000]")
                
            elif "slack" in b_type:
                # Map to Bala (Agency Delivery Lead)
                await conn.execute("""
                    UPDATE external_users
                    SET external_username = 'Bala (Delivery Lead)'
                    WHERE id = $1
                """, eu["id"])
                print(f"  [OK] Mapped Slack user {eu['external_user_id']} -> Bala (Delivery Lead) [Agency Delivery & Reviewer]")

        # 3. Seed Extended Room Roles
        print("\n--- 3. Seeding Extended Room Roles (reviewer, authorized-signer, on-call) ---")
        rooms = await conn.fetch("SELECT id, name FROM rooms")
        for r in rooms:
            rid = r["id"]
            rname = r["name"]
            
            # Add authorized-signer to acme-client / Telegram room
            if "client" in rname:
                role_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO room_roles (id, room_id, name, instructions, exclusive, eligibility, created_at, tenant_id)
                    VALUES ($1, $2, 'authorized-signer', 'Legal signatory authorized to approve SOW Amendments up to $5,000', true, NULL, $3, '00000000-0000-0000-0000-000000000000')
                    ON CONFLICT DO NOTHING
                """, role_id, rid, now)
                
            # Add reviewer & on-call to acme-delivery / Slack room
            if "delivery" in rname or "engineering" in rname or "intake" in rname:
                for rtitle in ["reviewer", "on-call"]:
                    role_id = str(uuid.uuid4())
                    await conn.execute("""
                        INSERT INTO room_roles (id, room_id, name, instructions, exclusive, eligibility, created_at, tenant_id)
                        VALUES ($1, $2, $3, $4, false, NULL, $5, '00000000-0000-0000-0000-000000000000')
                        ON CONFLICT DO NOTHING
                    """, role_id, rid, rtitle, f"Responsible for {rtitle}", now)

        print("  [OK] Room roles seeded successfully.")

        # 4. Seed ScopeKeeper Blueprint Template into Switch PostgreSQL
        print("\n--- 4. Seeding ScopeKeeper Template into templates table ---")
        template_id = "scopekeeper-enterprise-template"
        existing_tpl = await conn.fetchrow("SELECT id FROM templates WHERE id = $1", template_id)
        
        tpl_content = """version: 1
group:
  name: Acme Web Portal
  description: ScopeKeeper Autonomous Scope Governance & Client Desk
  color: "#4F46E5"
rooms:
  - name: acme-client
    description: Shared client room with Acme Inc. (Discord / Telegram)
    roles: [client-desk, authorized-signer]
  - name: acme-intake
    description: Agency handoff room between Scout, Clerk, and Sakthi (Lead PM)
    roles: [account-manager, client-desk]
  - name: acme-delivery
    description: Internal engineering room with Bala (Delivery Lead & Reviewer)
    roles: [delivery-lead, reviewer, on-call]
  - name: acme-audit
    description: Immutable contract governance & digital signature ledger
agents:
  - name: acme-scout
    display_name: Scout
    provider: gemini
  - name: clerk
    display_name: Clerk
    provider: python
  - name: acme-estimator
    display_name: Estimator
    provider: gemini
  - name: acme-builder
    display_name: Builder
    provider: gemini
"""
        if not existing_tpl:
            await conn.execute("""
                INSERT INTO templates (id, tenant_id, owner_id, name, description, kind, content, version, created_at, updated_at, read_visibility, write_visibility)
                VALUES ($1, '00000000-0000-0000-0000-000000000000', $2, 'ScopeKeeper Enterprise Governance', 'End-to-End Scope Creep Prevention & Autonomous Multi-Agent Agency Desk', 'blueprint', $3, 1, $4, $4, 'tenant', 'tenant')
            """, template_id, admin_user["id"] if admin_user else str(uuid.uuid4()), tpl_content, now)
            print("  [OK] Inserted ScopeKeeper Blueprint Template into templates table.")
        else:
            await conn.execute("UPDATE templates SET content = $1, updated_at = $2 WHERE id = $3", tpl_content, now, template_id)
            print("  [OK] Updated ScopeKeeper Blueprint Template.")

        print("\n✅ SEEDING COMPLETE: Switch Core is aligned with Harish, Dhana, Sakthi, and Bala.")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(seed())
