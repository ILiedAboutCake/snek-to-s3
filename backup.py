from datetime import date
import shutil
import logging
import os
import boto3
import json
import subprocess
import time
import tarfile
import requests
import time

START = time.time()

CONFIG_FILE = "config.json"

with open(CONFIG_FILE, "r") as cfgReadFile:
        try:
            cfg = json.load(cfgReadFile)
        except Exception as e:
            print("Unable to parse config.json: reason {}".format(e))
            exit()

s3 = boto3.client('s3', aws_access_key_id=cfg['s3_bucket_key_id'], aws_secret_access_key=cfg['s3_bucket_key_secret'])

def cleanup_local():
        path = os.path.join(os.getcwd(), cfg['folder_name'])
        cutoff = START - (cfg['keep_local_days'] * 86400)

        for root, dirs, files in os.walk(path, topdown=False):
                for dir in dirs:
                        fpath = os.path.join(path,dir)
                        if os.stat(fpath).st_mtime < cutoff:
                                print("CLEANUP: Removing DIR {} past local age set in config.".format(fpath))
                                shutil.rmtree(fpath)

def webhook(content):
        r = requests.post(cfg['webhook'], timeout=1, json={"content":content})
        print(r.status_code)

def bucket_size(day):
        total_size = 0
        for obj in boto3.resource('s3', aws_access_key_id=cfg['s3_bucket_key_id'], aws_secret_access_key=cfg['s3_bucket_key_secret']).Bucket(cfg['s3_bucket_name']).objects.filter(Prefix=day):
                total_size += obj.size
        return round(total_size / 1048576, 2)

def backup_folder():
    # should be backups/2019-04-20
    today_backupfolder = os.path.join(cfg['folder_name'], str(date.today()))

    #make the daily backup folder if it doesn't exist
    if not os.path.exists(today_backupfolder):
        os.makedirs(today_backupfolder)

    return today_backupfolder

def zip_folder(folder, name):
    d = shutil.make_archive(os.path.join(backup_folder(), name), 'zip', folder)
    return d

def targz_folder(folder, name):
    d = shutil.make_archive(os.path.join(backup_folder(), name), 'gztar', folder)
    return d

def copy_file(filename):
    shutil.copyfile(filename, os.path.join(backup_folder(), filename))

def copy_to_s3(filename):
    s3.upload_file(os.path.join(backup_folder(), filename), cfg['s3_bucket_name'], str(date.today())+"/"+filename)
    print("Uploaded: {}".format(filename))

def dump_db(database):
        sqlfile = backup_folder()+'/'+str(date.today())+'_'+database+'.sql'
        subprocess.Popen('mysqldump --defaults-extra-file='+cfg['mysqldump']+' --routines --events --triggers --single-transaction '+database+' > '+sqlfile, shell=True)
        time.sleep(1)

        path, filename = os.path.split(sqlfile)
        ret = backup_folder()+"/_"+filename+".tar.gz"
        farchive = tarfile.open(backup_folder()+"/_"+filename+".tar.gz", "w|gz")
        farchive.add(sqlfile, arcname=filename)
        farchive.close()

        print("DB: Gzipped as {} ".format(ret))
        os.remove(sqlfile)
        return ret

#gzip folders and send em off to s3
for folder in cfg['folders']:
        folder_safe = folder.replace("/","_")
        ret = targz_folder(folder, str(date.today())+folder_safe)
        print("FOLDERS: Gzipping {0} to {1}".format(folder, ret))
        path, filename = os.path.split(ret)
        copy_to_s3(filename)

#dumps misc files into 1 archive, best for cfg files
farchive = tarfile.open(backup_folder()+"/"+str(date.today())+"_miscfiles.tar.gz", "w|gz")
for file in cfg['files']:
        print("MISCFILES: Adding {}".format(file))
        farchive.add(file, arcname=file)
farchive.close()
copy_to_s3(str(date.today())+"_miscfiles.tar.gz")

#dumps local dbs to disk and uploads to S3
for db in cfg['mysql_dbs']:
        dbfile = dump_db(db)
        path, filename = os.path.split(dbfile)
        copy_to_s3(filename)

#cleanup the aged out backups
cleanup_local()

TIME_TAKEN = round(time.time() - START, 2)

copied_today = bucket_size(str(date.today()))
webhook("{0[webhook_tag]} The {0[webhook_nicejobname]} backup job has completed. `{1}MB` was uploaded to the S3 bucket `{0[s3_bucket_name]}`. Took {2} seconds.".format(cfg, copied_today, TIME_TAKEN))
