import motor.motor_asyncio
from datetime import datetime, timedelta


class MongoDB:
    _instances = {}

    def __new__(cls, uri: str, db_name: str):
        if (uri, db_name) not in cls._instances:
            instance = super().__new__(cls)

            instance.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            instance.db = instance.client[db_name]

            instance.user_data = instance.db["users"]
            instance.channel_data = instance.db["channels"]
            instance.premium_users = instance.db["pros"]

            instance.fsub_status = instance.db["fsub_status"]
            instance.request_sub = instance.db["request_sub"]

            cls._instances[(uri, db_name)] = instance

        return cls._instances[(uri, db_name)]

    # ================================================================
    # CHANNEL FUNCTIONS
    # ================================================================

    async def set_channels(self, channels: list[int]):
        await self.user_data.update_one(
            {"_id": 1},
            {"$set": {"channels": channels}},
            upsert=True
        )

    async def get_channels(self) -> list[int]:
        data = await self.user_data.find_one({"_id": 1})
        return data.get("channels", []) if data else []

    async def add_channel_user(self, channel_id: int, user_id: int):
        await self.channel_data.update_one(
            {"_id": channel_id},
            {"$addToSet": {"users": user_id}},
            upsert=True
        )

    async def remove_channel_user(self, channel_id: int, user_id: int):
        await self.channel_data.update_one(
            {"_id": channel_id},
            {"$pull": {"users": user_id}}
        )

    async def get_channel_users(self, channel_id: int) -> list[int]:
        doc = await self.channel_data.find_one(
            {"_id": channel_id}
        )

        return doc.get("users", []) if doc else []

    async def is_user_in_channel(
        self,
        channel_id: int,
        user_id: int
    ) -> bool:

        doc = await self.channel_data.find_one(
            {
                "_id": channel_id,
                "users": {"$in": [user_id]}
            },
            {"_id": 1}
        )

        return doc is not None

    # ================================================================
    # PREMIUM FUNCTIONS
    # ================================================================

    async def add_pro(
        self,
        user_id: int,
        expiry_date: datetime = None
    ):
        try:

            await self.premium_users.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "expiry_date": expiry_date
                    }
                },
                upsert=True
            )

            return True

        except Exception as e:

            print(
                f"Failed to add premium user: {e}"
            )

            return False

    async def remove_pro(self, user_id: int):

        try:

            await self.premium_users.delete_one(
                {"_id": user_id}
            )

            return True

        except Exception as e:

            print(
                f"Failed to remove premium user: {e}"
            )

            return False

    async def is_pro(self, user_id: int):

        doc = await self.premium_users.find_one(
            {"_id": user_id}
        )

        if not doc:
            return False

        # Legacy premium users
        if "expiry_date" not in doc:
            return True

        # Permanent premium
        if doc["expiry_date"] is None:
            return True

        # Expiry-based premium
        return doc["expiry_date"] > datetime.now()

    async def get_pros_list(self):

        current_time = datetime.now()

        cursor = self.premium_users.find(
            {
                "$or": [

                    {
                        "expiry_date": None
                    },

                    {
                        "expiry_date": {
                            "$exists": False
                        }
                    },

                    {
                        "expiry_date": {
                            "$gt": current_time
                        }
                    }

                ]
            }
        )

        return [
            doc["_id"]
            async for doc in cursor
        ]

    async def get_expiry_date(
        self,
        user_id: int
    ) -> datetime:

        doc = await self.premium_users.find_one(
            {"_id": user_id}
        )

        return (
            doc.get("expiry_date")
            if doc
            else None
        )

    # ================================================================
    # USER FUNCTIONS
    # ================================================================

    async def present_user(
        self,
        user_id: int
    ) -> bool:

        found = await self.user_data.find_one(
            {"_id": user_id}
        )

        return bool(found)

    async def add_user(
        self,
        user_id: int,
        ban: bool = False
    ):

        await self.user_data.insert_one(
            {
                "_id": user_id,
                "ban": ban
            }
        )

    async def full_userbase(self) -> list[int]:

        cursor = self.user_data.find()

        return [
            doc["_id"]
            async for doc in cursor
            if isinstance(doc.get("_id"), int)
        ]

    async def del_user(self, user_id: int):

        await self.user_data.delete_one(
            {"_id": user_id}
        )

    async def ban_user(self, user_id: int):

        await self.user_data.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "ban": True
                }
            }
        )

    async def unban_user(self, user_id: int):

        await self.user_data.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "ban": False
                }
            }
        )

    async def is_banned(
        self,
        user_id: int
    ) -> bool:

        user = await self.user_data.find_one(
            {"_id": user_id}
        )

        return (
            user.get("ban", False)
            if user
            else False
        )

    # ================================================================
    # FORCE SUB CHANNEL FUNCTIONS
    # ================================================================

    async def set_fsub_channels(
        self,
        fsub_data: dict
    ):

        await self.user_data.update_one(
            {"_id": "fsub_channels"},
            {
                "$set": {
                    "channels": fsub_data
                }
            },
            upsert=True
        )

    async def get_fsub_channels(self) -> dict:

        data = await self.user_data.find_one(
            {"_id": "fsub_channels"}
        )

        return (
            data.get("channels", {})
            if data
            else {}
        )

    async def add_fsub_channel(
        self,
        channel_id: int,
        channel_data: list
    ):

        current_data = await self.get_fsub_channels()

        current_data[str(channel_id)] = channel_data

        await self.set_fsub_channels(
            current_data
        )

    async def remove_fsub_channel(
        self,
        channel_id: int
    ):

        current_data = await self.get_fsub_channels()

        current_data.pop(
            str(channel_id),
            None
        )

        await self.set_fsub_channels(
            current_data
        )

    # ================================================================
    # SHORTENER SETTINGS
    # ================================================================

    async def set_shortner_settings(
        self,
        shortner_data: dict
    ):

        await self.user_data.update_one(
            {"_id": "shortner_settings"},
            {
                "$set": {
                    "settings": shortner_data
                }
            },
            upsert=True
        )

    async def get_shortner_settings(self) -> dict:

        data = await self.user_data.find_one(
            {"_id": "shortner_settings"}
        )

        return (
            data.get("settings", {})
            if data
            else {}
        )

    async def update_shortner_setting(
        self,
        key: str,
        value
    ):

        current_data = await self.get_shortner_settings()

        current_data[key] = value

        await self.set_shortner_settings(
            current_data
        )

    async def get_shortner_status(self) -> bool:

        settings = await self.get_shortner_settings()

        return settings.get(
            "enabled",
            True
        )

    async def set_shortner_status(
        self,
        enabled: bool
    ):

        await self.update_shortner_setting(
            "enabled",
            enabled
        )

    # ================================================================
    # SHORT START TOKEN FUNCTIONS
    # ================================================================

    async def create_short_start_token(
        self,
        payload: str
    ) -> str:

        import secrets

        for _ in range(20):

            token = (
                secrets.token_urlsafe(6)
                .replace("-", "")
                .replace("_", "")
            )[:8]

            exists = await self.user_data.find_one(
                {
                    "_id": f"short_start:{token}"
                }
            )

            if not exists:

                await self.user_data.insert_one(
                    {
                        "_id": f"short_start:{token}",
                        "payload": payload
                    }
                )

                return token

        raise RuntimeError(
            "Could not generate a unique short start token"
        )

    async def get_short_start_payload(
        self,
        token: str
    ):

        data = await self.user_data.find_one(
            {
                "_id": f"short_start:{token}"
            }
        )

        return (
            data.get("payload")
            if data
            else None
        )

    # ================================================================
    # FSUB STATUS FUNCTIONS
    # ================================================================

    async def update_fsub_status(
        self,
        user_id: int,
        channel_id: int,
        status: str
    ):

        await self.fsub_status.update_one(
            {
                "user_id": user_id,
                "channel_id": channel_id
            },
            {
                "$set": {
                    "status": status,
                    "last_updated": datetime.now()
                }
            },
            upsert=True
        )

    async def get_fsub_status(
        self,
        user_id: int,
        channel_id: int
    ) -> str:

        doc = await self.fsub_status.find_one(
            {
                "user_id": user_id,
                "channel_id": channel_id
            }
        )

        return (
            doc.get("status")
            if doc
            else None
        )

    async def remove_fsub_status(
        self,
        user_id: int,
        channel_id: int
    ):

        await self.fsub_status.delete_one(
            {
                "user_id": user_id,
                "channel_id": channel_id
            }
        )

    async def get_user_fsub_statuses(
        self,
        user_id: int
    ) -> dict:

        cursor = self.fsub_status.find(
            {
                "user_id": user_id
            }
        )

        statuses = {}

        async for doc in cursor:

            statuses[
                doc["channel_id"]
            ] = doc["status"]

        return statuses

    async def clear_expired_fsub_statuses(
        self,
        days: int = 7
    ):

        cutoff_date = (
            datetime.now()
            - timedelta(days=days)
        )

        await self.fsub_status.delete_many(
            {
                "last_updated": {
                    "$lt": cutoff_date
                }
            }
        )

    # ================================================================
    # JOIN REQUEST FUNCTIONS
    # ================================================================

    async def add_join_request(
        self,
        user_id: int,
        channel_id: int,
        request_id: int = None
    ):

        await self.request_sub.update_one(
            {
                "user_id": user_id,
                "channel_id": channel_id
            },
            {
                "$set": {

                    "request_id": request_id,

                    "status": "pending",

                    "submitted_at": datetime.now(),

                    "last_updated": datetime.now()

                }
            },
            upsert=True
        )

    async def update_join_request_status(
        self,
        user_id: int,
        channel_id: int,
        status: str
    ):

        await self.request_sub.update_one(
            {
                "user_id": user_id,
                "channel_id": channel_id
            },
            {
                "$set": {

                    "status": status,

                    "last_updated": datetime.now()

                }
            }
        )

    async def get_join_request_status(
        self,
        user_id: int,
        channel_id: int
    ) -> str:

        doc = await self.request_sub.find_one(
            {
                "user_id": user_id,
                "channel_id": channel_id
            }
        )

        return (
            doc.get("status")
            if doc
            else None
        )

    async def has_submitted_join_request(
        self,
        user_id: int,
        channel_id: int
    ) -> bool:

        doc = await self.request_sub.find_one(
            {
                "user_id": user_id,
                "channel_id": channel_id
            }
        )

        return doc is not None

    async def remove_join_request(
        self,
        user_id: int,
        channel_id: int
    ):

        await self.request_sub.delete_one(
            {
                "user_id": user_id,
                "channel_id": channel_id
            }
        )

    async def get_pending_requests_for_channel(
        self,
        channel_id: int
    ) -> list:

        cursor = self.request_sub.find(
            {
                "channel_id": channel_id,
                "status": "pending"
            }
        )

        requests = []

        async for doc in cursor:

            requests.append(
                {
                    "user_id": doc["user_id"],
                    "request_id": doc.get("request_id"),
                    "submitted_at": doc["submitted_at"]
                }
            )

        return requests

    async def clear_old_join_requests(
        self,
        days: int = 30
    ):

        cutoff_date = (
            datetime.now()
            - timedelta(days=days)
        )

        await self.request_sub.delete_many(
            {
                "submitted_at": {
                    "$lt": cutoff_date
                }
            }
        )

    # ================================================================
    # DATABASE CLEANUP
    # ================================================================

    async def cleanup_database(self):

        try:

            await self.clear_expired_fsub_statuses(7)

            await self.clear_old_join_requests(30)

            await self.cleanup_orphaned_records()

            await self.cleanup_expired_verifications()

            return True

        except Exception as e:

            print(
                f"Database cleanup error: {e}"
            )

            return False

    async def cleanup_orphaned_records(self):

        try:

            users = await self.full_userbase()

            async for doc in self.fsub_status.find(
                {
                    "user_id": {
                        "$nin": users
                    }
                }
            ):

                await self.fsub_status.delete_one(
                    {
                        "_id": doc["_id"]
                    }
                )

            async for doc in self.request_sub.find(
                {
                    "user_id": {
                        "$nin": users
                    }
                }
            ):

                await self.request_sub.delete_one(
                    {
                        "_id": doc["_id"]
                    }
                )

            return True

        except Exception as e:

            print(
                f"Error cleaning orphaned records: {e}"
            )

            return False

    # ================================================================
    # FSUB STATISTICS
    # ================================================================

    async def get_comprehensive_fsub_statistics(self):

        try:

            fsub_count = await self.fsub_status.count_documents({})

            request_count = await self.request_sub.count_documents({})

            pending_requests = await self.request_sub.count_documents(
                {
                    "status": "pending"
                }
            )

            approved_requests = await self.request_sub.count_documents(
                {
                    "status": "approved"
                }
            )

            rejected_requests = await self.request_sub.count_documents(
                {
                    "status": "rejected"
                }
            )

            status_breakdown = {}

            async for doc in self.fsub_status.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$status",
                            "count": {
                                "$sum": 1
                            }
                        }
                    }
                ]
            ):

                status_breakdown[
                    doc["_id"]
                ] = doc["count"]

            channel_stats = {}

            async for doc in self.fsub_status.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$channel_id",
                            "count": {
                                "$sum": 1
                            }
                        }
                    }
                ]
            ):

                channel_stats[
                    doc["_id"]
                ] = doc["count"]

            yesterday = (
                datetime.now()
                - timedelta(days=1)
            )

            recent_fsub_updates = await self.fsub_status.count_documents(
                {
                    "last_updated": {
                        "$gte": yesterday
                    }
                }
            )

            recent_requests = await self.request_sub.count_documents(
                {
                    "submitted_at": {
                        "$gte": yesterday
                    }
                }
            )

            return {

                "total_fsub_records": fsub_count,

                "total_join_requests": request_count,

                "pending_requests": pending_requests,

                "approved_requests": approved_requests,

                "rejected_requests": rejected_requests,

                "status_breakdown": status_breakdown,

                "channel_statistics": channel_stats,

                "recent_activity": {

                    "fsub_updates_24h": recent_fsub_updates,

                    "join_requests_24h": recent_requests

                }

            }

        except Exception as e:

            print(
                f"Error getting comprehensive fsub statistics: {e}"
            )

            return {}

    async def get_user_activity_summary(
        self,
        user_id: int
    ):

        try:

            fsub_statuses = await self.get_user_fsub_statuses(
                user_id
            )

            join_requests = []

            async for doc in self.request_sub.find(
                {
                    "user_id": user_id
                }
            ):

                join_requests.append(
                    {
                        "channel_id": doc["channel_id"],

                        "status": doc["status"],

                        "submitted_at": doc["submitted_at"],

                        "last_updated": doc["last_updated"]
                    }
                )

            is_banned = await self.is_banned(
                user_id
            )

            is_premium = await self.is_pro(
                user_id
            )

            return {

                "user_id": user_id,

                "is_banned": is_banned,

                "is_premium": is_premium,

                "fsub_statuses": fsub_statuses,

                "join_request_history": join_requests,

                "total_channels_joined": len(
                    [
                        status
                        for status in fsub_statuses.values()
                        if status == "joined"
                    ]
                ),

                "total_requests_submitted": len(
                    join_requests
                )

            }

        except Exception as e:

            print(
                f"Error getting user activity summary "
                f"for {user_id}: {e}"
            )

            return {}

    async def get_channel_activity_summary(
        self,
        channel_id: int
    ):

        try:

            channel_users = await self.get_channel_users(
                channel_id
            )

            status_counts = {}

            async for doc in self.fsub_status.aggregate(
                [
                    {
                        "$match": {
                            "channel_id": channel_id
                        }
                    },

                    {
                        "$group": {

                            "_id": "$status",

                            "count": {
                                "$sum": 1
                            }

                        }
                    }

                ]
            ):

                status_counts[
                    doc["_id"]
                ] = doc["count"]

            request_stats = {}

            async for doc in self.request_sub.aggregate(
                [
                    {
                        "$match": {
                            "channel_id": channel_id
                        }
                    },

                    {
                        "$group": {

                            "_id": "$status",

                            "count": {
                                "$sum": 1
                            }

                        }
                    }

                ]
            ):

                request_stats[
                    doc["_id"]
                ] = doc["count"]

            week_ago = (
                datetime.now()
                - timedelta(days=7)
            )

            recent_joins = await self.fsub_status.count_documents(
                {

                    "channel_id": channel_id,

                    "status": "joined",

                    "last_updated": {
                        "$gte": week_ago
                    }

                }
            )

            recent_requests = await self.request_sub.count_documents(
                {

                    "channel_id": channel_id,

                    "submitted_at": {
                        "$gte": week_ago
                    }

                }
            )

            return {

                "channel_id": channel_id,

                "total_users": len(
                    channel_users
                ),

                "status_breakdown": status_counts,

                "request_statistics": request_stats,

                "recent_activity_7d": {

                    "new_joins": recent_joins,

                    "new_requests": recent_requests

                }

            }

        except Exception as e:

            print(
                f"Error getting channel activity summary "
                f"for {channel_id}: {e}"
            )

            return {}

    async def bulk_update_user_statuses(
        self,
        updates: list
    ):

        try:

            operations = []

            for update in updates:

                user_id = update["user_id"]

                channel_id = update["channel_id"]

                status = update["status"]

                from pymongo import UpdateOne

                operations.append(
                    UpdateOne(

                        {
                            "user_id": user_id,
                            "channel_id": channel_id
                        },

                        {
                            "$set": {

                                "status": status,

                                "last_updated": datetime.now()

                            }
                        },

                        upsert=True

                    )
                )

            if operations:

                result = await self.fsub_status.bulk_write(
                    operations
                )

                return result

            return None

        except Exception as e:

            print(
                f"Error in bulk update user statuses: {e}"
            )

            return None

    async def sync_channel_members(
        self,
        channel_id: int,
        current_members: list
    ):

        try:

            stored_users = await self.get_channel_users(
                channel_id
            )

            users_to_add = (
                set(current_members)
                - set(stored_users)
            )

            users_to_remove = (
                set(stored_users)
                - set(current_members)
            )

            for user_id in users_to_add:

                await self.add_channel_user(
                    channel_id,
                    user_id
                )

                await self.update_fsub_status(
                    user_id,
                    channel_id,
                    "joined"
                )

            for user_id in users_to_remove:

                await self.remove_channel_user(
                    channel_id,
                    user_id
                )

                await self.update_fsub_status(
                    user_id,
                    channel_id,
                    "left"
                )

            return {

                "added": len(
                    users_to_add
                ),

                "removed": len(
                    users_to_remove
                ),

                "synced": True

            }

        except Exception as e:

            print(
                f"Error syncing channel members: {e}"
            )

            return {

                "synced": False,

                "error": str(e)

            }

    async def export_fsub_data(
        self,
        channel_id: int = None
    ):

        try:

            export_data = {

                "export_timestamp": (
                    datetime.now()
                    .isoformat()
                ),

                "fsub_statuses": [],

                "join_requests": []

            }

            filter_query = (
                {
                    "channel_id": channel_id
                }

                if channel_id

                else {}
            )

            async for doc in self.fsub_status.find(
                filter_query
            ):

                doc["_id"] = str(
                    doc["_id"]
                )

                if "last_updated" in doc:

                    doc[
                        "last_updated"
                    ] = (
                        doc[
                            "last_updated"
                        ].isoformat()
                    )

                export_data[
                    "fsub_statuses"
                ].append(doc)

            async for doc in self.request_sub.find(
                filter_query
            ):

                doc["_id"] = str(
                    doc["_id"]
                )

                if "submitted_at" in doc:

                    doc[
                        "submitted_at"
                    ] = (
                        doc[
                            "submitted_at"
                        ].isoformat()
                    )

                if "last_updated" in doc:

                    doc[
                        "last_updated"
                    ] = (
                        doc[
                            "last_updated"
                        ].isoformat()
                    )

                export_data[
                    "join_requests"
                ].append(doc)

            return export_data

        except Exception as e:

            print(
                f"Error exporting fsub data: {e}"
            )

            return None

    async def get_fsub_statistics(self):

        try:

            fsub_count = await self.fsub_status.count_documents({})

            request_count = await self.request_sub.count_documents({})

            pending_requests = await self.request_sub.count_documents(
                {
                    "status": "pending"
                }
            )

            return {

                "fsub_status_records": fsub_count,

                "join_request_records": request_count,

                "pending_requests": pending_requests

            }

        except Exception as e:

            print(
                f"Error getting fsub statistics: {e}"
            )

            return {}

    # ================================================================
    # DATABASE CHANNEL FUNCTIONS
    # ================================================================

    async def set_db_channels(
        self,
        db_channels_data: dict
    ):

        await self.user_data.update_one(
            {"_id": "db_channels"},
            {
                "$set": {
                    "channels": db_channels_data
                }
            },
            upsert=True
        )

    async def get_db_channels(self) -> dict:

        data = await self.user_data.find_one(
            {"_id": "db_channels"}
        )

        return (
            data.get("channels", {})
            if data
            else {}
        )

    async def add_db_channel(
        self,
        channel_id: int,
        channel_data: dict
    ):

        current_data = await self.get_db_channels()

        current_data[
            str(channel_id)
        ] = channel_data

        await self.set_db_channels(
            current_data
        )

    async def remove_db_channel(
        self,
        channel_id: int
    ):

        current_data = await self.get_db_channels()

        current_data.pop(
            str(channel_id),
            None
        )

        await self.set_db_channels(
            current_data
        )

    async def update_db_channel(
        self,
        channel_id: int,
        channel_data: dict
    ):

        current_data = await self.get_db_channels()

        if str(channel_id) in current_data:

            current_data[
                str(channel_id)
            ].update(
                channel_data
            )

            await self.set_db_channels(
                current_data
            )

    async def get_primary_db_channel(self) -> int:

        db_channels = await self.get_db_channels()

        for channel_id_str, channel_data in db_channels.items():

            if channel_data.get(
                "is_primary",
                False
            ):

                return int(
                    channel_id_str
                )

        return None

    async def set_primary_db_channel(
        self,
        channel_id: int
    ):

        db_channels = await self.get_db_channels()

        for ch_id, ch_data in db_channels.items():

            ch_data[
                "is_primary"
            ] = False

        if str(channel_id) in db_channels:

            db_channels[
                str(channel_id)
            ][
                "is_primary"
            ] = True

        await self.set_db_channels(
            db_channels
        )

    async def get_active_db_channels(self) -> dict:

        db_channels = await self.get_db_channels()

        active_channels = {}

        for channel_id_str, channel_data in db_channels.items():

            if channel_data.get(
                "is_active",
                True
            ):

                active_channels[
                    channel_id_str
                ] = channel_data

        return active_channels

    async def toggle_db_channel_status(
        self,
        channel_id: int
    ):

        db_channels = await self.get_db_channels()

        if str(channel_id) in db_channels:

            current_status = db_channels[
                str(channel_id)
            ].get(
                "is_active",
                True
            )

            new_status = not current_status

            db_channels[
                str(channel_id)
            ][
                "is_active"
            ] = new_status

            await self.set_db_channels(
                db_channels
            )

            return new_status

        return None

    # ================================================================
    # BOT SETTINGS FUNCTIONS
    # ================================================================

    async def set_bot_settings(
        self,
        settings_data: dict
    ):

        await self.user_data.update_one(
            {"_id": "bot_settings"},
            {
                "$set": {
                    "settings": settings_data
                }
            },
            upsert=True
        )

    async def get_bot_settings(self) -> dict:

        data = await self.user_data.find_one(
            {"_id": "bot_settings"}
        )

        return (
            data.get("settings", {})
            if data
            else {}
        )

    async def update_bot_setting(
        self,
        key: str,
        value
    ):

        current_data = await self.get_bot_settings()

        current_data[key] = value

        await self.set_bot_settings(
            current_data
        )

    async def get_bot_setting(
        self,
        key: str,
        default=None
    ):

        settings = await self.get_bot_settings()

        return settings.get(
            key,
            default
        )

    # ================================================================
    # MESSAGE SETTINGS FUNCTIONS
    # ================================================================

    async def set_messages_settings(
        self,
        messages_data: dict
    ):

        await self.user_data.update_one(
            {"_id": "messages_settings"},
            {
                "$set": {
                    "messages": messages_data
                }
            },
            upsert=True
        )

    async def get_messages_settings(self) -> dict:

        data = await self.user_data.find_one(
            {"_id": "messages_settings"}
        )

        return (
            data.get("messages", {})
            if data
            else {}
        )

    async def update_message_setting(
        self,
        key: str,
        value: str
    ):

        current_data = await self.get_messages_settings()

        current_data[key] = value

        await self.set_messages_settings(
            current_data
        )

    async def get_message_setting(
        self,
        key: str,
        default: str = ""
    ):

        messages = await self.get_messages_settings()

        return messages.get(
            key,
            default
        )

    # ================================================================
    # ADMIN SETTINGS
    # ================================================================

    async def set_admins_list(
        self,
        admins_list: list
    ):

        await self.user_data.update_one(
            {"_id": "admins_list"},
            {
                "$set": {
                    "admins": admins_list
                }
            },
            upsert=True
        )

    async def get_admins_list(self) -> list:

        data = await self.user_data.find_one(
            {"_id": "admins_list"}
        )

        return (
            data.get("admins", [])
            if data
            else []
        )

    async def add_admin(
        self,
        admin_id: int
    ):

        current_admins = await self.get_admins_list()

        if admin_id not in current_admins:

            current_admins.append(
                admin_id
            )

            await self.set_admins_list(
                current_admins
            )

            return True

        return False

    async def remove_admin(
        self,
        admin_id: int
    ):

        current_admins = await self.get_admins_list()

        if admin_id in current_admins:

            current_admins.remove(
                admin_id
            )

            await self.set_admins_list(
                current_admins
            )

            return True

        return False

    # ================================================================
    # BATCH SETTINGS
    # ================================================================

    async def save_all_settings(
        self,
        bot_settings: dict,
        messages: dict,
        admins: list
    ):

        try:

            await self.set_bot_settings(
                bot_settings
            )

            await self.set_messages_settings(
                messages
            )

            await self.set_admins_list(
                admins
            )

            return True

        except Exception as e:

            print(
                f"Error saving all settings: {e}"
            )

            return False

    async def load_all_settings(self) -> dict:

        try:

            bot_settings = await self.get_bot_settings()

            messages = await self.get_messages_settings()

            admins = await self.get_admins_list()

            shortner_settings = await self.get_shortner_settings()

            return {

                "bot_settings": bot_settings,

                "messages": messages,

                "admins": admins,

                "shortner_settings": shortner_settings

            }

        except Exception as e:

            print(
                f"Error loading all settings: {e}"
            )

            return {

                "bot_settings": {},

                "messages": {},

                "admins": [],

                "shortner_settings": {}

            }

    # ================================================================
    # ACCESS SETTINGS
    # ================================================================

    async def get_access_settings(self):

        data = await self.db[
            "access_settings"
        ].find_one(
            {
                "_id": "main"
            }
        ) or {}

        defaults = {

            "credit_price": 1,

            "credit_reward": 1,

            "token_hours": 24,

            "shortener_expiry": 10,

            "min_verify_seconds": 30,

            "purchase_url": ""

        }

        defaults.update(
            {
                key: value

                for key, value in data.items()

                if key != "_id"
            }
        )

        return defaults

    async def update_access_setting(
        self,
        key,
        value
    ):

        await self.db[
            "access_settings"
        ].update_one(
            {
                "_id": "main"
            },
            {
                "$set": {
                    key: value
                }
            },
            upsert=True
        )

    # ================================================================
    # ACCESS MODE
    # ================================================================

    async def get_access_mode(self):

        data = await self.db[
            "access_settings"
        ].find_one(
            {
                "_id": "mode"
            }
        ) or {}

        return data.get(
            "mode",
            "shortener"
        )

    async def set_access_mode(
        self,
        mode
    ):

        allowed_modes = (

            "shortener",

            "credit",

            "token",

            "free"

        )

        if mode not in allowed_modes:

            raise ValueError(
                "Invalid access mode"
            )

        await self.db[
            "access_settings"
        ].update_one(
            {
                "_id": "mode"
            },
            {
                "$set": {
                    "mode": mode
                }
            },
            upsert=True
        )

    # ================================================================
    # CREDIT SYSTEM
    # ================================================================

    async def get_credit(
        self,
        user_id
    ):

        data = await self.user_data.find_one(
            {
                "_id": user_id
            }
        ) or {}

        return max(
            0,
            int(
                data.get(
                    "credit",
                    0
                )
            )
        )

    async def change_credit(
        self,
        user_id,
        amount,
        floor_zero=False
    ):

        current_credit = await self.get_credit(
            user_id
        )

        new_credit = (
            current_credit
            + int(amount)
        )

        if floor_zero:

            new_credit = max(
                0,
                new_credit
            )

        await self.user_data.update_one(
            {
                "_id": user_id
            },
            {
                "$set": {
                    "credit": new_credit
                }
            },
            upsert=True
        )

        return new_credit

    async def list_credit_users(self):

        cursor = self.user_data.find(
            {
                "credit": {
                    "$gt": 0
                }
            }
        ).sort(
            "credit",
            -1
        )

        return [
            user
            async for user in cursor
        ]

    # ================================================================
    # PENDING VERIFICATION SYSTEM
    # ================================================================

    async def create_pending_verification(
        self,
        user_id,
        payload,
        kind
    ):

        import secrets

        # ------------------------------------------------------------
        # Reuse ONLY an active and unused verification
        # ------------------------------------------------------------

        existing = await self.db[
            "pending_verifications"
        ].find_one(
            {

                "user_id": user_id,

                "payload": payload,

                "kind": kind,

                "verified": False,

                "expires_at": {
                    "$gt": datetime.now()
                }

            }
        )

        if existing:

            return existing

        settings = await self.get_access_settings()

        verification_token = None

        # Generate a unique token
        for _ in range(20):

            token = (

                secrets.token_urlsafe(10)

                .replace("-", "")

                .replace("_", "")

            )[:12]

            already_exists = await self.db[
                "pending_verifications"
            ].find_one(
                {
                    "_id": token
                }
            )

            if not already_exists:

                verification_token = token

                break

        if not verification_token:

            raise RuntimeError(
                "Could not generate a unique verification token"
            )

        expiry_minutes = int(
            settings.get(
                "shortener_expiry",
                10
            )
        )

        created_at = datetime.now()

        expires_at = (

            created_at

            + timedelta(
                minutes=expiry_minutes
            )

        )

        verification_data = {

            "_id": verification_token,

            "user_id": user_id,

            "payload": payload,

            "kind": kind,

            "created_at": created_at,

            "expires_at": expires_at,

            "verified": False,

            "verified_at": None

        }

        await self.db[
            "pending_verifications"
        ].insert_one(
            verification_data
        )

        return verification_data

    async def get_pending_verification(
        self,
        verification_token
    ):

        return await self.db[
            "pending_verifications"
        ].find_one(
            {
                "_id": verification_token
            }
        )

    async def consume_pending_verification(
        self,
        verification_token
    ):

        """
        Atomically consumes a verification.

        Returns True only if the verification:
        - Exists
        - Has not already been used
        - Has not expired
        """

        result = await self.db[
            "pending_verifications"
        ].update_one(
            {

                "_id": verification_token,

                "verified": False,

                "expires_at": {
                    "$gt": datetime.now()
                }

            },

            {

                "$set": {

                    "verified": True,

                    "verified_at": datetime.now()

                }

            }

        )

        return result.modified_count == 1

    async def cleanup_expired_verifications(self):

        """
        Removes old verification records.

        Expired records and already-used records older than
        one day are removed.
        """

        now = datetime.now()

        used_cutoff = (
            now
            - timedelta(days=1)
        )

        try:

            await self.db[
                "pending_verifications"
            ].delete_many(
                {

                    "$or": [

                        {

                            "expires_at": {
                                "$lt": now
                            }

                        },

                        {

                            "verified": True,

                            "verified_at": {
                                "$lt": used_cutoff
                            }

                        }

                    ]

                }
            )

            return True

        except Exception as e:

            print(
                f"Verification cleanup error: {e}"
            )

            return False

    # ================================================================
    # TOKEN ACCESS SYSTEM
    # ================================================================

    async def set_token_access(
        self,
        user_id,
        hours
    ):

        expiry_time = (

            datetime.now()

            + timedelta(
                hours=int(hours)
            )

        )

        await self.db[
            "token_access"
        ].update_one(
            {
                "_id": user_id
            },
            {
                "$set": {
                    "until": expiry_time
                }
            },
            upsert=True
        )

        return expiry_time

    async def get_token_access(
        self,
        user_id
    ):

        data = await self.db[
            "token_access"
        ].find_one(
            {
                "_id": user_id
            }
        )

        return (
            data.get("until")
            if data
            else None
        )
