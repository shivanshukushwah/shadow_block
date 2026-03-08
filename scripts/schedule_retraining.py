from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess

def retrain_job():
    subprocess.run(["python", "d:\\AI_shadow_block\\backend\\scripts\\retrain_model.py"])

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(retrain_job, "cron", hour=0, minute=0)
    scheduler.start()