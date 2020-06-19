db.getSiblingDB("mhub")
db.getSiblingDB("celery")
db.mhub.createIndex({"job_id": 1})
db.mhub.createIndex({"timestamp": 1, "state": 1})
db.mhub.createIndex({"timestamp": 1, "output_path": 1})
db.mhub.createIndex({"timestamp": 1, "queue": 1})
db.mhub.createIndex({"timestamp": 1, "geometry": "2dsphere"})
db.mhub.createIndex({"timestamp": 1})
db.createUser(
    {
        "user" : "mhub",
        "pwd" : "REDACTED_API_KEY",
        "roles" : [
            {
                "role" : "dbOwner",
                "db" : "admin"
            },
            {
                "role" : "dbOwner",
                "db" : "mhub",
            },
            {
                "role" : "dbOwner",
                "db" : "celery"
            }
        ]
    }
)