 # Snek to S3

 Backup LAMP* stack servers easily locally + remote S3 bucket.

 *Can be used to backup any files and folders, as well as MariaDB/MySQL DBs

 ## Runnin it

 Python3 is required. I have tested with python 3.5+. Install modules with `python3 -m pip install -r requirements.txt`

 Script also requires some S3 tokens, and a Discord Webhook URL to post backup finish messages to.

 ## The Cloud

Before starting you should have some knowledge of AWS IAM roles and access keys: https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html

I would recommend only allowing `PutObject` write access to prevent rogue actions/key theft from deleting your remote backups. [Use a S3 lifecycle rule to rotate off aged out backups.](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/create-lifecycle.html)

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:ListBucket*"
            ],
            "Resource": [
                "arn:aws:s3:::website-prod-backup/*",
                "arn:aws:s3:::website-prod-backup"
            ]
        }
    ]
}
```

## The Config

Everything is controlled with `config.json`. Use the attached mysql.cnf to store the SQL db access keys. I recommend setting both config.json and mysql.cnf permissions to 600.

## The Automation

Run nightly as a cron job. The user this runs as should have read access to all your files/folder configured in config.json.

```
0 12 * * * (cd /home/cake/backups/; /usr/bin/python3 backup.py)
```

## The Costs

When done properly, the cloud can be inexpensive. I use this script to backup ~100MB/daily for 14 days of stored backups. Monthly S3 costs run about $1-2/month. I'm sure you could get this cost lower using reduced redundancy or glacier policies.
